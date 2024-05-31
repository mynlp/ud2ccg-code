import os
import sys
import copy
import logging


logger = logging.getLogger(__name__)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class TRange:
    def __init__(self, start_idx, end_idx, type_changed=False):
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.type_changed = type_changed

    def __repr__(self):
        return ':'.join([str(self.start_idx), str(self.end_idx)])

    def __key(self):
        return self.__repr__()

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, TRange):
            if (self.type_changed and other.type_changed) or (not self.type_changed and not other.type_changed):
                return self.__key() == other.__key()
            else:
                return False
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, TRange):
            return self.start_idx < other.start_idx
        return NotImplemented

    def contains(self, idx):
        # both start and end indices are inclusive
        if self.start_idx <= idx <= self.end_idx:
            return True
        else:
            return False

    def contains_range(self, tr):
        # both start and end indices are inclusive
        if self.start_idx <= tr.start_idx and self.end_idx >= tr.end_idx:
            return True
        else:
            return False

    @staticmethod
    def merge_range(tr1, tr2):
        return TRange(min(tr1.start_idx, tr2.start_idx), max(tr1.end_idx, tr2.end_idx))

    @staticmethod
    def new_range(idx, old_range):
        if idx < old_range.start_idx:
            return TRange(idx, old_range.end_idx)
        elif idx > old_range.end_idx:
            return TRange(old_range.start_idx, idx)
        else:
            return old_range


# check if there exists a crossing dependency in this tree
def check_crossing_dependencies(sentence):
    range_list = []

    for token in sentence:
        token_idx = token.idx
        token_head = token.head
        new_range = TRange(min(token_idx, token_head), max(token_idx, token_head))

        for r in range_list:
            # if not one range contains the other
            if not new_range.contains_range(r) and not r.contains_range(new_range):
                if (max(new_range.start_idx, r.start_idx) - min(new_range.end_idx, r.end_idx)) < 0:
                    return True

        range_list.append(new_range)

    return False


# Check if current treebank contains train/dev/test splits
def check_data_splits(treebank_dir):
    has_train = False
    for filename in os.listdir(treebank_dir):
        if 'train.conllu' in filename:
            has_train = True
            break
    return has_train


# Check if current treebank's surface is stripped
def check_surface_tokens(treebank_dir):
    readme_path = os.path.join(treebank_dir, "README.md")
    if not os.path.exists(readme_path):
        readme_path = os.path.join(treebank_dir, "README.txt")
        if not os.path.exists(readme_path):
            return False

    with open(readme_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("Includes text: "):
                include_text = line.strip().split(' ')[-1]
                if include_text != 'yes':
                    return False
                return True


# Check if the percentages of deprel "dep" and postag "X" in sentences
# of current treebank pass a certain threshold
def check_dep_X(treebank_dir, threshold=0.9):
    total_dep_count = 0
    total_X_count = 0
    total_sentences = 0

    for filename in os.listdir(treebank_dir):
        if '.conllu' in filename:
            sentences = []

            with open(os.path.join(treebank_dir, filename), 'r') as f:
                sentence_deprels = []
                sentence_postags = []

                # add empty line at the end to imitate conllu sentence break
                lines = f.readlines()
                lines.append('')

                for line in lines:
                    # empty line in conllu file indicates sentence break
                    if line.strip() == '':
                        if len(sentence_deprels) > 0 and len(sentence_postags) > 0:
                            stats = (copy.deepcopy(sentence_deprels), copy.deepcopy(sentence_postags))
                            sentences.append(stats)

                        sentence_deprels = []
                        sentence_postags = []
                        continue

                    # skip comments in conllu file
                    if line.startswith('#'):
                        continue

                    # split field by tab
                    fields = line.strip().split('\t')

                    # 0 = word index (starting at 1)
                    # 1 = word form
                    # 3 = UPOS
                    # 6 = head of current word index
                    # 7 = UD relation
                    try:
                        deprel = fields[7]
                        postag = fields[3]
                    except ValueError:
                        pass
                    else:
                        sentence_deprels.append(deprel)
                        sentence_postags.append(postag)

            dep_count = 0
            X_count = 0
            for stats in sentences:
                sentence_deprels = stats[0]
                sentence_postags = stats[1]

                if 'dep' in sentence_deprels:
                    dep_count += 1

                if 'X' in sentence_postags:
                    X_count += 1

            total_dep_count += dep_count
            total_X_count += X_count
            total_sentences += len(sentences)

    if total_sentences == 0:
        return False
    else:
        dep_pct = total_dep_count / total_sentences
        X_pct = total_X_count / total_sentences

        if dep_pct >= threshold or X_pct >= threshold:
            # eprint('  {:>3} appears in {} of {} sentences ({:.2%})'.format('dep', total_dep_count, total_sentences, dep_pct))
            # eprint('  {:>3} appears in {} of {} sentences ({:.2%})'.format('X', total_X_count, total_sentences, X_pct))
            return False

    return True


# A treebank will not be converted if it has one or more of the following:
# - lack of train/dev/test splits
# - surface tokens are stripped
# - the percentages of deprel "dep" and postag "X" in sentences > a certain threshold
# - questionable annotations (e.g. Chinese treebanks)
def check_valid_treebank(treebank_dir,
                         check_data_splits_opt=True,
                         check_surface_tokens_opt=True,
                         check_dep_X_opt=True):
    logger.info('Checking validity: {}'.format(treebank_dir))

    if check_data_splits_opt:
        check1 = check_data_splits(treebank_dir)
    else:
        check1 = True

    if check_surface_tokens_opt:
        check2 = check_surface_tokens(treebank_dir)
    else:
        check2 = True

    if check_dep_X_opt:
        check3 = check_dep_X(treebank_dir)
    else:
        check3 = True

    is_valid = check1 and check2 and check3

    if not is_valid:
        if not check1:
            eprint('  INVALID - no training split')
        if not check2:
            eprint('  INVALID - surface stripped')
        if not check3:
            eprint('  INVALID - too many "dep" or "X"')
    else:
        logger.info('  VALID')

    return is_valid
