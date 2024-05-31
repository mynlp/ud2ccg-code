To run the code for a single .conllu file, execute:
```commandline
python -m ud2ccg.main --conllu-path data/UD_English-EWT/en_ewt-ud-dev.conllu \
                      --sud-conllu-path data/UD_English-EWT/en_ewt-sud-dev.conllu \
                      --up-conllup-path data/UD_English-EWT/en_ewt-up-dev_with-span.conllup \
                      --export-path data/converted \
                      --complete-output-only
```

For the entire UD:
```commandline
python -m ud2ccg.main --ud-path data/has_eud/ud-treebanks-v2.9 \
                      --sud-path data/has_eud/sud-treebanks-v2.11 \
                      --up-path data/has_eud/up-treebanks-v2.9 \
                      --export-path data/has_eud/converted \
                      --complete-output-only
```
`--sud-conllu-path`/`--sud-path` and `--up-conllup-path`/`--up-path` are optional.
