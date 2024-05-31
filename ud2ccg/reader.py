import copy
import logging

logger = logging.getLogger(__name__)


class UDToken:
    def __init__(self, idx, form, upos, feats, head, deprel, eud):
        self.idx = idx  # index of this token
        self.form = form
        self.upos = upos
        self.feats = feats
        self.head = head  # index of head
        self.deprel = deprel
        self.eud = eud


class UDSentence:
    def __init__(self, sentence, sent_id, text):
        self.sentence = sentence
        self.sent_id = sent_id
        self.text = text


def read_conllu(path, remove_quotation_marks=True, remove_empty_nodes=True, change_punct=True, return_index_remap=False):
    sentences = []

    index_remaps = dict()

    with open(path, "r") as f:
        # add empty line at the end to imitate conllu sentence break
        lines = f.readlines()
        lines.append("")

        sentence = []
        index_remap = dict()
        index_remap[0] = 0
        offset = 0
        sentence_idx = 0
        sent_id = "None"
        text = "None"

        # get all heads of each sentence;
        # necessary for later steps, as we don't want to remove quotation marks
        # that are heads of something else
        if remove_quotation_marks:
            all_heads = dict()
            head_list = set()
            sentence_idx_ = 0
            for line in lines:
                # empty line in conllu file indicates sentence break
                if line.strip() == "":
                    if len(head_list) > 0:
                        all_heads[sentence_idx_] = head_list

                    head_list = set()
                    sentence_idx_ += 1

                    continue

                # skip comments in conllu file
                if line.startswith("#"):
                    continue

                # split field by tab
                fields = line.strip().split("\t")

                if remove_empty_nodes:
                    if "." in fields[0] or "-" in fields[0]:
                        continue

                current_head = int(fields[6])
                head_list.add(current_head)

        for line in lines:
            # empty line in conllu file indicates sentence break
            if line.strip() == "":
                # shift indices
                if remove_quotation_marks:
                    try:
                        for token in sentence:
                            if token.idx in index_remap:
                                token.idx = index_remap[token.idx]
                                token.head = index_remap[token.head]

                            # adjust the indices of enhanced dependencies
                            eud = token.eud
                            if eud != "_":
                                parts = eud.split("|")
                                new_parts = list()
                                for part in parts:
                                    first_colon_idx = part.index(":")
                                    eud_head = part[:first_colon_idx]
                                    if "." not in eud_head and "-" not in eud_head:
                                        eud_head = int(eud_head)
                                        eud_deprel = part[first_colon_idx + 1:]

                                        new_eud_head = index_remap[eud_head]
                                        new_part = str(new_eud_head) + ':' + eud_deprel
                                        new_parts.append(new_part)

                                if len(new_parts) > 0:
                                    new_eud = '|'.join(new_parts)
                                else:
                                    new_eud = "_"

                                token.eud = new_eud

                    except KeyError:
                        logger.exception(
                            f"sentence: {' '.join([token.form for token in sentence])}\nindex_remap: {index_remap}"
                        )

                if len(sentence) > 0:
                    new_sentence = UDSentence(copy.deepcopy(sentence), sent_id, text)
                    sentences.append(new_sentence)

                if return_index_remap:
                    index_remaps[sent_id] = index_remap

                sentence = []
                index_remap = dict()
                index_remap[0] = 0
                offset = 0
                sentence_idx += 1
                sent_id = "None"
                text = "None"

                continue

            # extract sent_id
            # skip other comments in conllu file
            if line.startswith("#"):
                if line.startswith("# sent_id"):
                    parts = line.strip().split(" ")
                    sent_id = parts[-1]
                    continue
                elif line.startswith("# text ="):
                    text = line[9:].strip()
                    continue
                else:
                    continue

            # split field by tab
            fields = line.strip().split("\t")

            if remove_empty_nodes:
                if "." in fields[0] or "-" in fields[0]:
                    continue

            # remove quotation marks if necessary
            # do not remove when the quotation mark is
            #  - NOUN, PROPN, PRON, NUM, SYM
            #  - root
            #  - head of something else
            if remove_quotation_marks:
                if (
                    fields[1] in ['"', "’’", ",,", "''", '”']
                    and fields[3] not in ["NOUN", "PROPN", "PRON", "NUM", "SYM"]
                    and fields[7] not in ["root"]
                    and int(fields[0]) not in all_heads[sentence_idx]
                ):
                    offset += 1
                    continue
                else:
                    index_remap[int(fields[0])] = int(fields[0]) - offset

            # change types of some punctuation marks
            form = fields[1]
            if change_punct:
                if form in "『』「」【】《》〈〉（）〔〕«»()[]{}-–—":
                    fields[7] = "punct2"

            # 0 = word index (starting at 1)
            # 1 = word form
            # 3 = UPOS
            # 5 = features
            # 6 = head of current word index
            # 7 = UD relation
            # 8 = EUD relations
            try:
                current_token = UDToken(idx=int(fields[0]),
                                        form=fields[1],
                                        upos=fields[3],
                                        feats=fields[5],
                                        head=int(fields[6]),
                                        deprel=fields[7],
                                        eud=fields[8])
            except ValueError:
                logger.exception("")
            else:
                sentence.append(current_token)

    if return_index_remap:
        return sentences, index_remaps
    else:
        return sentences


class SUDToken:
    def __init__(self, idx, head, deprel):
        self.idx = idx   # index of this token
        self.head = head   # index of head
        self.deprel = deprel
        self.deps = set()   # a list of dependents of this token


def read_sud_conllu(path, remove_quotation_marks=True, remove_empty_nodes=True):
    # a dictionary with key = sent_id
    # and value is a list of tokens and their dependents in a sentence
    sentences = dict()

    with open(path, 'r') as f:
        # add empty line at the end to imitate conllu sentence break
        lines = f.readlines()
        lines.append("")

        sent_id = "None"
        sentence = []

        # variables for remapping head indices when quotation marks are removed
        index_remap = dict()
        index_remap[0] = 0
        offset = 0
        sentence_idx = 0

        # get all heads of each sentence;
        # necessary for later steps, as we don't want to remove quotation marks
        # that are heads of something else
        if remove_quotation_marks:
            all_heads = dict()
            head_list = set()
            sentence_idx_ = 0
            for line in lines:
                # empty line in conllu file indicates sentence break
                if line.strip() == "":
                    if len(head_list) > 0:
                        all_heads[sentence_idx_] = head_list

                    head_list = set()
                    sentence_idx_ += 1

                    continue

                # skip comments in conllu file
                if line.startswith("#"):
                    continue

                # split field by tab
                fields = line.strip().split("\t")

                if remove_empty_nodes:
                    if "." in fields[0] or "-" in fields[0]:
                        continue

                current_head = int(fields[6])
                head_list.add(current_head)

        for line in lines:
            # empty line in conllu file indicates sentence break
            if line.strip() == "":
                # shift indices
                if remove_quotation_marks:
                    try:
                        for token in sentence:
                            if token.idx in index_remap:
                                token.idx = index_remap[token.idx]
                                token.head = index_remap[token.head]
                    except KeyError:
                        logger.exception(
                            f"sentence: {' '.join([str(token.idx) for token in sentence])}\nindex_remap: {index_remap}"
                        )

                # another loop to fill the deps attribute
                for token in sentence:
                    head = token.head
                    if head > 0:
                        sentence[head-1].deps.add(token.idx)

                # handling of comp:aux
                # dependents of the aux verb also become dependents of the copula verb
                for token in sentence:
                    if token.deprel == 'comp:aux':
                        sentence[token.idx-1].deps.update(sentence[token.head-1].deps)
                        sentence[token.idx-1].deps.remove(token.idx)
                        sentence[token.idx-1].deps.add(token.head)

                # add this sentence to the list of sentences
                sentences[sent_id] = sentence

                # reset variables
                sent_id = "None"
                sentence = []
                index_remap = dict()
                index_remap[0] = 0
                offset = 0
                sentence_idx += 1

                continue

            # extract sent_id
            # skip other comments in conllu file
            if line.startswith("#"):
                if line.startswith("# sent_id"):
                    parts = line.strip().split(" ")
                    sent_id = parts[-1]
                    continue
                else:
                    continue

            # split field by tab
            fields = line.strip().split("\t")

            if remove_empty_nodes:
                if "." in fields[0] or "-" in fields[0]:
                    continue

            # remove quotation marks if necessary
            # do not remove when the quotation mark is
            #  - NOUN, PROPN, PRON, NUM, SYM
            #  - root
            #  - head of something else
            if remove_quotation_marks:
                if (
                        fields[1] in ['"', "’’", ",,", "''"]
                        and fields[3] not in ["NOUN", "PROPN", "PRON", "NUM", "SYM"]
                        and fields[7] not in ["root"]
                        and int(fields[0]) not in all_heads[sentence_idx]
                ):
                    offset += 1
                    continue
                else:
                    index_remap[int(fields[0])] = int(fields[0]) - offset

            current_token = SUDToken(idx=int(fields[0]),
                                     head=int(fields[6]),
                                     deprel=fields[7])

            sentence.append(current_token)

    return sentences


class UPToken:
    def __init__(self, idx, argheads, argspans):
        self.idx = idx  # index of this token
        self.argheads = argheads
        self.argspans = argspans


def read_conllup(conllup_path, conllu_path, remove_quotation_marks=True, remove_empty_nodes=True):
    ud_sentences, index_remaps = read_conllu(conllu_path,
                                             remove_quotation_marks=remove_quotation_marks,
                                             remove_empty_nodes=remove_empty_nodes,
                                             return_index_remap=True)

    sentences = dict()

    with open(conllup_path, "r") as f:
        # add empty line at the end to imitate conllu sentence break
        lines = f.readlines()
        lines.append("")

        sent_id = "None"
        sentence = []

        for line in lines:
            # empty line in conllu file indicates sentence break
            if line.strip() == "":
                if remove_quotation_marks:
                    index_remap = index_remaps[sent_id]
                    for token in sentence:
                        if token.idx in index_remap:
                            token.idx = index_remap[token.idx]

                        # adjust the indices of argheads if remove_quotation_marks
                        argheads = token.argheads
                        if argheads != "_":
                            parts = argheads.split("|")
                            new_parts = list()
                            for part in parts:
                                first_colon_idx = part.index(":")
                                label = part[:first_colon_idx]
                                token_idx = int(part[first_colon_idx + 1:])

                                if token_idx in index_remap:
                                    new_token_idx = index_remap[token_idx]
                                    new_part = label + ':' + str(new_token_idx)
                                else:
                                    new_part = part

                                new_parts.append(new_part)

                            new_argheads = '|'.join(new_parts)
                            token.argheads = new_argheads

                        # adjust the indices of argspans if remove_quotation_marks
                        argspans = token.argspans
                        if argspans != "_":
                            parts = argspans.split("|")
                            new_parts = list()
                            for part in parts:
                                first_colon_idx = part.index(":")
                                label = part[:first_colon_idx]
                                span = part[first_colon_idx + 1:]

                                span_parts = span.split('-')
                                span_start = int(span_parts[0])
                                span_end = int(span_parts[1])

                                if span_start in index_remap:
                                    new_span_start = index_remap[span_start]
                                else:
                                    new_span_start = span_start

                                if span_end in index_remap:
                                    new_span_end = index_remap[span_end]
                                else:
                                    new_span_end = span_end

                                new_part = label + ':' + str(new_span_start) + '-' + str(new_span_end)

                                new_parts.append(new_part)

                            new_argspans = '|'.join(new_parts)
                            token.argspans = new_argspans

                new_sentence = copy.deepcopy(sentence)
                sentences[sent_id] = new_sentence

                sentence = []
                sent_id = "None"

                continue

            # extract sent_id
            # skip other comments in conllu file
            if line.startswith("#"):
                if line.startswith("# sent_id"):
                    parts = line.strip().split(" ")
                    sent_id = parts[-1]
                    continue
                else:
                    continue

            # split field by tab
            fields = line.strip().split("\t")

            if remove_empty_nodes:
                if "." in fields[0] or "-" in fields[0]:
                    continue

            idx = int(fields[0])
            pred = fields[1]
            argheads = fields[2]
            argspans = fields[3]

            if pred != '_':
                current_token = UPToken(idx=idx, argheads=argheads, argspans=argspans)
                sentence.append(current_token)

    return sentences
