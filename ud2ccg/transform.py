import os
import logging
import tqdm
from typing import List, Dict
from collections import namedtuple
from ud2ccg.cat import Functor, apply_default_slash_direction, apply_default_category
from ud2ccg.dtree import DTree
from ud2ccg.btree import BTree
from ud2ccg.preprocessing import preprocess_ap, preprocess_conj, preprocess_ref
from ud2ccg.reader import read_conllu, read_sud_conllu, read_conllup, UDSentence, SUDToken, UPToken
from ud2ccg.rules.apply import apply_rules
from ud2ccg.parser.tree import Token
from ud2ccg.format import to_auto
from ud2ccg.utils import check_crossing_dependencies
from ud2ccg.evaluate import evaluate_against_up_with_span


logger = logging.getLogger(__name__)


# what this function does:
# - create dtree
# - split dtree by depth
# - for each sub-dtree (recursion):
#   + transform into ccgtree
#   + do category assignment
# - returns a list of lexical categories
def convert_single(
        ud_sentence: UDSentence,
        sud_sentence: List[SUDToken] = None,
        up_sentence: List[UPToken] = None,
        slash_stats: Dict[str, int] = None
):
    sentence = ud_sentence.sentence  # a list of UDTokens
    sent_id = ud_sentence.sent_id

    # store UD data in a dependency tree data structure
    dtree = DTree.from_sentence(sentence)

    #####################
    #   PREPROCESSING   #
    #####################

    # preprocess adpositional phrases
    if up_sentence is not None:
        preprocess_ap(dtree, up_sentence)

    # preprocess coordination structures (with EUD)
    preprocess_conj(dtree)

    # preprocess ref dependencies in EUD
    preprocess_ref(dtree)

    ##################
    #   CONVERSION   #
    ##################

    # convert dtree to binary tree
    btree = BTree.from_dtree(dtree)

    # skip if this tree is too deep
    if btree.height() > 27:
        logger.debug(f'skipped {sent_id}\t{btree.height()}')
        return None, None, None, None

    # apply category assignment rules
    apply_rules(btree, dtree, subdtree_root_cat=None)

    # remove dummy ROOT node from btree
    btree_root = btree.get_root()
    btree_root_children = btree.get_children(btree_root)
    for child in btree_root_children:
        if btree.get_category_type(child) == 'ROOT':
            btree.remove_node(child)
    btree.remove_node(btree_root)

    #########################################
    #   POSTPROCESSING & STATS COLLECTION   #
    #########################################

    # extract supertags
    supertags = dict()
    conj_feats = dict()
    for leaf in btree.get_leaf_nodes():
        leaf_node = btree.get_btree_node(leaf)
        leaf_idx = leaf_node['idx']
        supertags[leaf_idx] = leaf_node['category']
        conj_feats[leaf_idx] = leaf_node['conj']

    # in case of 1-node tree
    if len(supertags) == 0:
        leaf_node = btree.get_btree_node(btree.get_root())
        leaf_idx = leaf_node['idx']
        supertags[leaf_idx] = leaf_node['category']
        conj_feats[leaf_idx] = leaf_node['conj']

    # convert ":t" index marker to actual index
    def traverse_category(cat):
        if cat is not None:
            index = str(cat.index)
            if ":t" in index:
                pos = int(index[:-2])
                index_at_pos = supertags[pos].index
                cat.index = index_at_pos
            if isinstance(cat, Functor):
                traverse_category(cat.left)
                traverse_category(cat.right)

    for idx, supertag in supertags.items():
        traverse_category(supertag)

    # we will later feed these toks and tags to a non-statistical parser
    # that produces every possible tree from these supertags
    # TODO to be updated
    toks = list()
    tags = list()
    for idx in sorted(supertags):
        if idx > 0:  # ignore root
            dtree_node = dtree.get_dtree_node(idx)
            tok = Token(
                word=dtree_node['form'],
                pos=dtree_node['upos'],
                feat=conj_feats[idx]
            )
            toks.append(tok)
            this_tag = supertags[idx]
            tags.append(this_tag)

            # collect slash direction from S|NP-type categories (experimental)
            if str(this_tag) in ['S\\NP']:
                slash_stats['\\'] += 1
            elif str(this_tag) in ['S/NP']:
                slash_stats['/'] += 1

    return toks, tags, btree, dtree


def convert_conllu(
        conllu_path: str,
        export_path: str,
        sud_conllu_path: str = None,
        up_conllup_path: str = None,
        convert_crossing_dependencies: bool = False,
        complete_output_only: bool = False
):
    logger.info("==============================================")
    logger.info(f"Converting: {conllu_path}")
    logger.info(f"  SUD path: {sud_conllu_path}")
    logger.info(f"   UP path: {up_conllup_path}")

    basename = os.path.basename(conllu_path)
    filename = os.path.splitext(basename)[0]

    # export paths
    auto_path = os.path.join(export_path, filename + ".auto")
    lexicon_path = os.path.join(export_path, filename + ".lexicon")
    f_auto = open(auto_path, "w")
    f_lex = open(lexicon_path, "w")

    # some conversion stats
    num_cross = 0
    num_converted = 0

    # used to store lexemes from converted trees
    lexicon = dict()
    Lexeme = namedtuple("Lexeme", ["word", "category"])

    # read UD data
    logger.info("Reading UD data...")
    ud_sentences = read_conllu(conllu_path)

    # read SUD data
    sud_sentences = None
    if sud_conllu_path is not None:
        logger.info("Reading SUD data...")
        sud_sentences = read_sud_conllu(sud_conllu_path)

    # read UP data
    up_sentences = None
    if up_conllup_path is not None:
        logger.info("Reading UP data...")
        up_sentences = read_conllup(up_conllup_path, conllu_path)

    # collecting slash direction of S|NP categories across the entire treebank (experimental);
    # the reason is | slash comes from our rules that assign S|NP to phrases without subject;
    # the most common slash will be applied to any left-over '|' in the treebank
    slash_stats = dict()
    slash_stats['/'] = 0
    slash_stats['\\'] = 0

    ############################
    #   FIRST PASS - CONVERT   #
    ############################

    logger.info("First pass (conversion)...")

    first_pass = dict()

    for ud_sentence in tqdm.tqdm(ud_sentences, disable=False):
        to_convert = True
        if not convert_crossing_dependencies:
            if check_crossing_dependencies(ud_sentence.sentence):
                num_cross += 1
                to_convert = False

        if to_convert:
            sent_id = ud_sentence.sent_id

            # get corresponding SUD sentence
            sud_sentence = None
            if sud_sentences is not None:
                if sent_id in sud_sentences:
                    sud_sentence = sud_sentences[sent_id]

            # get corresponding UP sentence
            up_sentence = None
            if up_sentences is not None:
                if sent_id in up_sentences:
                    up_sentence = up_sentences[sent_id]

            # convert sentence
            toks, tags, btree, dtree = convert_single(ud_sentence,
                                                      sud_sentence,
                                                      up_sentence,
                                                      slash_stats)

            if toks is not None:
                first_pass[sent_id] = (toks, tags, btree, dtree)

    # determine most common slash direction
    if slash_stats['/'] > slash_stats['\\']:
        default_slash = '/'
    else:
        default_slash = '\\'

    logger.info(f"%with crossing dependencies = "
                f"{num_cross}/{len(ud_sentences)} = "
                f"{100.0 * num_cross / len(ud_sentences):.2f}%")
    logger.info(f"Default slash direction for {filename}: {default_slash}")
    logger.info(f"Forward slash count: {slash_stats['/']}")
    logger.info("Backward slash count: {}".format(slash_stats['\\']))

    #######################################
    #   SECOND PASS - FIX SLASH & EXPORT  #
    #######################################

    logger.info("Second pass (slash fixing & export)...")

    conversion_results = dict()

    for sent_id in tqdm.tqdm(first_pass, disable=False):
        toks, tags, btree, dtree = first_pass[sent_id]

        for tag in tags:
            # apply most common slash direction
            apply_default_slash_direction(tag, default_slash)

            # in case of unsolved variable category
            apply_default_category(tag)

        # export to CCGBank .auto file format
        autof = to_auto(btree, dtree)

        # check if the converted tree is complete (no assigned category)
        is_complete = True
        for tag in tags:
            if 'X_' in str(tag) or '|' in str(tag) or 'None' in str(tag):
                is_complete = False
                break

        if is_complete:
            num_converted += 1

        if (complete_output_only and is_complete) or (not complete_output_only):
            # we don't really need anything other than toks and tags
            # since the head indices are already unified
            conversion_results[sent_id] = (toks, tags)

            # write to .auto file
            f_auto.write('ID={} PARSER=GOLD NUMPARSE=1\n'.format(sent_id))
            f_auto.write(str(autof))
            f_auto.write('\n')

            # collect lexemes
            for i in range(len(toks)):
                word = toks[i].word
                category = str(tags[i])

                lex = Lexeme(word=word, category=category)
                if category is None or str(category) == 'None':
                    pass
                if lex in lexicon:
                    lexicon[lex] = lexicon[lex] + 1
                else:
                    lexicon[lex] = 1

    # write lexicon to file
    lexicon_keys = sorted(lexicon.keys())
    for k in lexicon_keys:
        f_lex.write('{:<15}\t{:>50}\t\t{}\n'.format(k.word, k.category, lexicon[k]))

    # evaluate against UP
    logger.info("----------------------------------------------")
    logger.info("Evaluating conversion results against UP...")

    if up_conllup_path is not None:
        recall, precision, f1, core_arg_recall, mod_arg_recall \
            = evaluate_against_up_with_span(conversion_results, up_sentences)

        # summarize stats
        conversion_rate = num_converted / len(ud_sentences)

        # print
        logger.info(f"  Input treebank  : {filename}")
        logger.info(f"  Conversion rate : {conversion_rate:.4f}")
        logger.info(f"  Recall          : {recall:.4f}")
        logger.info(f"  Precision       : {precision:.4f}")
        logger.info(f"  F1              : {f1:.4f}")
        logger.info(f"  Core-arg recall : {core_arg_recall:.4f}")
        logger.info(f"  Mod-arg recall  : {mod_arg_recall:.4f}")

    # close writers
    f_auto.close()
    f_lex.close()
