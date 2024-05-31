from typing import List
from ud2ccg.cat import Category, Functor
from ud2ccg.parser.tree import Token


# return a list of tuples (i, j), where:
# - i = token index of head
# - j = token index of dependent
def extract_pas(tokens: List[Token], supertags: List[Category]):
    # create a map of head index -> token index (position in sentence)
    hidx_to_tidx_map = dict()
    modifiers = list()

    for i, supertag in enumerate(supertags, 1):
        if supertag is not None:
            supertag_hidx = str(supertag.index)
            if supertag_hidx not in hidx_to_tidx_map:
                hidx_to_tidx_map[supertag_hidx] = list()
            hidx_to_tidx_map[supertag_hidx].append(i)

            # if category is of the form (X_i|X_i)_j, we consider this a modifier-type category
            if isinstance(supertag, Functor):
                if supertag.left.index == supertag.right.index and supertag.left.index != supertag.index:
                    modifiers.append(i)

    # extract the arguments of each functor
    pas = list()
    for i, supertag in enumerate(supertags, 1):
        if isinstance(supertag, Functor):
            arguments = list()

            def extract_arguments(cat):
                if isinstance(cat, Functor):
                    argument = cat.right
                    arguments.append(argument)

                    result = cat.left
                    extract_arguments(result)

            extract_arguments(supertag)

            # map head index of argument to its position (token index) in the sentence
            for argument in arguments:
                argument_hidx = str(argument.index)

                argument_tidx = None
                if ':t' in argument_hidx:
                    if argument_hidx[:-2] != 'None':
                        argument_tidx = [int(argument_hidx[:-2])]
                else:
                    if argument_hidx in hidx_to_tidx_map:
                        argument_tidx = hidx_to_tidx_map[argument_hidx]

                # argument_tidx can be a list because of rules for coordination;
                # conjuncts can have the same index
                if argument_tidx is not None:
                    for j in argument_tidx:
                        # check if this dependency between i and j is valid;
                        # need to prevent crossing dependency between two conjuncts
                        # TODO there may be a better way to do this
                        is_valid = True
                        i_feat = tokens[i-1].feat
                        j_feat = tokens[j-1].feat
                        if ':' in i_feat and ':' in j_feat:
                            i_common_conj_idx = i_feat.split(':')[0]
                            j_common_conj_idx = j_feat.split(':')[0]
                            if i_common_conj_idx == j_common_conj_idx:
                                i_conj_idx = i_feat.split(':')[1]
                                j_conj_idx = j_feat.split(':')[1]
                                if i_conj_idx != j_conj_idx:
                                    is_valid = False

                        # flip direction of dependency projected from modifiers
                        if is_valid:
                            if i in modifiers:
                                pas.append((j, i))
                            else:
                                pas.append((i, j))

    return pas


# return a dictionary:
# - key = sent_id
# - values = a list of tuples (pred_idx, arg_idx, label)
def extract_pas_from_conllup(up_sentences):
    all_pas = dict()

    for sent_id in up_sentences:
        pas = list()

        for up_token in up_sentences[sent_id]:
            pred_idx = up_token.idx
            argheads = up_token.argheads

            if argheads != "_":
                parts = argheads.split("|")
                for part in parts:
                    first_colon_idx = part.index(":")
                    label = part[:first_colon_idx]
                    arg_idx = int(part[first_colon_idx + 1:])

                    pas.append((pred_idx, arg_idx, label))

        all_pas[sent_id] = pas

    return all_pas


# return a dictionary:
# - key = sent_id
# - values = a list of tuples (pred_idx, arg_span, label)
def extract_pas_from_conllup_with_span(up_sentences):
    all_pas = dict()

    for sent_id in up_sentences:
        pas = list()

        for up_token in up_sentences[sent_id]:
            pred_idx = up_token.idx
            argspans = up_token.argspans

            if argspans != "_":
                parts = argspans.split("|")
                for part in parts:
                    first_colon_idx = part.index(":")
                    label = part[:first_colon_idx]
                    span = part[first_colon_idx + 1:]

                    span_parts = span.split('-')
                    span_start = int(span_parts[0])
                    span_end = int(span_parts[1])

                    pas.append((pred_idx, (span_start, span_end), label))

        all_pas[sent_id] = pas

    return all_pas


# span-based evaluation
def evaluate_against_up_with_span(conversion_results, up_sentences):
    # extract PAS from UP data
    all_up_pas = extract_pas_from_conllup_with_span(up_sentences)

    # recall measures
    num_target_pas = 0
    recall_true_positives = 0
    labelled_num_target_pas = dict()
    labelled_true_positives = dict()

    # precision measures
    num_result_pas = 0
    precision_true_positives = 0
    precision_false_positives = 0

    # loop
    for sent_id in conversion_results:
        conversion_result = conversion_results[sent_id]
        toks, tags = conversion_result

        # extract PAS from conversion result
        result_pas = extract_pas(toks, tags)

        # UP's PAS of this sentence
        up_pas = all_up_pas[sent_id]

        # calculate num_target_pas for recall
        for target_pas in up_pas:
            num_target_pas += 1

            # UP's PAS tuple: (pred_idx, (span_start, span_end), label)
            target_pas_label = target_pas[2]

            if target_pas_label not in labelled_num_target_pas:
                labelled_num_target_pas[target_pas_label] = 0
                labelled_true_positives[target_pas_label] = 0

            labelled_num_target_pas[target_pas_label] += 1

        # calculate precision, only for predicates that appear in UP;
        # in case of multiple word-word dependencies attaching to the same span,
        # only count them as 1 for recall measure,
        # but count them as multiple for precision measure
        up_pas_unlabelled = dict()
        up_pas_preds = set()

        # group up predicates that appear in UP
        for pas in up_pas:
            pas_label = pas[2]
            pas_unlabelled = (pas[0], pas[1])
            pas_pred = pas[0]

            up_pas_unlabelled[pas_unlabelled] = pas_label
            up_pas_preds.add(pas_pred)

        # CCG-extracted PAS tuple: (pred_idx, arg_idx)
        already_counted_target_pas = set()

        for pas in result_pas:
            pas_pred = pas[0]

            # only count predicates that appear in UP
            if pas_pred in up_pas_preds:
                num_result_pas += 1

                # check if this PAS is in UP
                is_correct = False
                for target_pas in up_pas_unlabelled.keys():
                    # UP's PAS tuple: (pred_idx, (span_start, span_end), label)
                    target_pred = target_pas[0]
                    target_arg_span_start = target_pas[1][0]
                    target_arg_span_end = target_pas[1][1]

                    # the PAS is considered correct if its arg_idx is inside UP's arg_span
                    if pas[0] == target_pred:
                        if target_arg_span_start <= pas[1] <= target_arg_span_end:
                            is_correct = True

                            if target_pas not in already_counted_target_pas:
                                already_counted_target_pas.add(target_pas)

                                # to calculate recall, do not count as correct again if it has already been counted
                                correct_label = up_pas_unlabelled[target_pas]
                                labelled_true_positives[correct_label] += 1
                                recall_true_positives += 1

                            break

                if is_correct:
                    precision_true_positives += 1
                else:
                    precision_false_positives += 1

    #################################################################
    #   calculate core and non-core (modifier) dependency results   #
    #################################################################

    num_argm_target_pas = 0
    argm_true_positives = 0

    num_non_argm_target_pas = 0
    non_argm_true_positives = 0

    for label in sorted(labelled_num_target_pas):
        if 'ARGM' not in label and 'AM' not in label:
            num_non_argm_target_pas += labelled_num_target_pas[label]
            non_argm_true_positives += labelled_true_positives[label]
        else:
            num_argm_target_pas += labelled_num_target_pas[label]
            argm_true_positives += labelled_true_positives[label]

    core_arg_recall = non_argm_true_positives / num_non_argm_target_pas
    mod_arg_recall = argm_true_positives / num_argm_target_pas

    #################################
    #   calculate overall results   #
    #################################

    recall = recall_true_positives / num_target_pas
    precision = precision_true_positives / num_result_pas
    f1 = 2 * (recall * precision) / (recall + precision)

    return recall, precision, f1, core_arg_recall, mod_arg_recall
