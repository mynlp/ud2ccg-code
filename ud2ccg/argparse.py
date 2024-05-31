import argparse


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--ud-path', action='store', dest='ud_path',
                        help='path to UD directory (e.g. ud-treebanks-v2.9)')

    parser.add_argument('--up-path', action='store', dest='up_path',
                        help='path to UP directory (e.g. up-treebanks-v2.9)')

    parser.add_argument('--sud-path', action='store', dest='sud_path',
                        help='path to SUD directory (e.g. sud-treebanks-v2.11)')

    parser.add_argument('--conllu-path', action='store', dest='conllu_path',
                        help='path to .conllu file (e.g. UD_English-EWT/en_ewt-ud-train.conllu)')

    parser.add_argument('--up-conllup-path', action='store', dest='up_conllup_path',
                        help='path to UP .conllup file')

    parser.add_argument('--sud-conllu-path', action='store', dest='sud_conllu_path',
                        help='path to SUD .conllu file')

    parser.add_argument('--export-path', action='store', dest='export_path', required=True,
                        help='where converted treebank(s) should be stored')

    parser.add_argument('--convert-crossing-dependencies', action='store_true', default=False,
                        dest='convert_crossing_dependencies',
                        help='whether to convert trees with crossing dependencies or not')

    parser.add_argument('--complete-output-only', action='store_true', default=False,
                        dest='complete_output_only',
                        help='only export fully converted trees')

    parser.add_argument('--debug', action='store_true', default=False, dest='debug',
                        help='print debug statements when running')

    args = parser.parse_args()

    return args
