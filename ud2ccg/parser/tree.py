# modified from: https://github.com/masashi-y/depccg
import re
from typing import NamedTuple, List, Iterator, Union


dunder_pattern = re.compile("__.*__")
protected_pattern = re.compile("_.*")


class Token(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __getattr__(self, item):
        if dunder_pattern.match(item) or protected_pattern.match(item):
            return super().__getattr__(item)
        return self[item]

    def __repr__(self):
        res = super().__repr__()
        return f'Token({res})'
