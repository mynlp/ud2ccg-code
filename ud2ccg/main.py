import os
import sys
import logging
from pathlib import Path
from ud2ccg.argparse import parse_args
from ud2ccg.transform import convert_conllu
from ud2ccg.utils import check_valid_treebank

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def main(args):
    ud_path = args.ud_path
    up_path = args.up_path
    sud_path = args.sud_path

    conllu_path = args.conllu_path
    sud_conllu_path = args.sud_conllu_path
    up_conllup_path = args.up_conllup_path

    if (ud_path is None and conllu_path is None) or (ud_path is not None and conllu_path is not None):
        logger.error("Please verify path to UD directory or .conllu file")
        sys.exit(1)

    export_path = args.export_path
    convert_crossing_dependencies = args.convert_crossing_dependencies
    complete_output_only = args.complete_output_only
    debug = args.debug

    if ud_path is not None:
        logger.info(f"Input UD path: {ud_path}")
    if conllu_path is not None:
        logger.info(f"Input .conllu path: {conllu_path}")
    logger.info(f"Export path: {export_path}")
    logger.info(f"Convert trees with crossing dependencies: {convert_crossing_dependencies}")
    logger.info(f"Only export fully converted trees: {complete_output_only}")
    logger.info(f"Debug mode: {debug}")

    # if given a conllu file instead of a folder
    if conllu_path is not None:
        convert_conllu(conllu_path,
                       export_path,
                       sud_conllu_path,
                       up_conllup_path,
                       convert_crossing_dependencies,
                       complete_output_only)

    # if given a folder instead of a conllu file
    if ud_path is not None:
        num_treebanks = 0
        num_valid_treebanks = 0

        for root, subdirs, files in sorted(os.walk(ud_path)):
            if 'UD_' in os.path.basename(root):
                num_treebanks += 1
                is_valid = check_valid_treebank(root, check_data_splits_opt=False)

                if is_valid:
                    num_valid_treebanks += 1
                    dirpath, dirname = os.path.split(root)
                    dirname_parts = dirname[3:].split('-')
                    lang = dirname_parts[0]
                    treebank = dirname_parts[1]

                    converted_path = os.path.join(export_path, dirname)
                    Path(converted_path).mkdir(parents=True, exist_ok=True)

                    for file in files:
                        if file.endswith('.conllu'):
                            filename = os.path.splitext(file)[0]
                            filename_parts = filename.split('-')
                            treebank_name = filename_parts[0]
                            split = filename_parts[2]

                            conllu_path = os.path.join(root, file)

                            # get corresponding UP path
                            if up_path is not None:
                                up_treebank_dir = 'UP_' + lang + '-' + treebank
                                up_treebank_file = '-'.join([treebank_name, 'up', split]) + '.conllup'
                                up_conllup_path = os.path.join(up_path, up_treebank_dir, up_treebank_file)
                                if not os.path.isfile(up_conllup_path):
                                    up_conllup_path = None

                            # get corresponding SUD path
                            if sud_path is not None:
                                sud_treebank_dir = 'SUD_' + lang + '-' + treebank
                                sud_treebank_file = '-'.join([treebank_name, 'sud', split]) + '.conllu'
                                sud_conllu_path = os.path.join(sud_path, sud_treebank_dir, sud_treebank_file)
                                if not os.path.isfile(sud_conllu_path):
                                    sud_conllu_path = None

                            convert_conllu(conllu_path,
                                           converted_path,
                                           sud_conllu_path,
                                           up_conllup_path,
                                           convert_crossing_dependencies,
                                           complete_output_only)


if __name__ == "__main__":
    args = parse_args()
    main(args)
