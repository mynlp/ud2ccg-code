# modified from: https://github.com/masashi-y/depccg
from typing import Optional, Callable, Tuple, TypeVar
from dataclasses import dataclass
import re

X = TypeVar('X')
Pair = Tuple[X, X]

cat_split = re.compile(r'([\[\]\(\)/\\|<>])')
punctuations = [',', '.', ';', ':', 'LRB', 'RRB', 'conj', '*START*', '*END*']


class Feature(object):
    def __repr__(self) -> str:
        return str(self)

    @classmethod
    def parse(cls, text: str) -> 'Feature':
        return UnaryFeature(text)


@dataclass(frozen=True, repr=False)
class UnaryFeature(Feature):
    """Common feature type widely used in many CCGBanks.
    This assumes None or "X" values as representing a variable feature.
    As commonly done in the parsing literature, the 'nb' variable is treated
    sometimes as not existing, i.e., NP[conj] and NP[nb] can match.
    """

    value: Optional[str] = None

    def __str__(self) -> str:
        return self.value if self.value is not None else ''

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self == Feature.parse(other)
        elif not isinstance(other, UnaryFeature):
            return False
        return self.value == other.value

    def unifies(self, other: 'UnaryFeature') -> bool:
        return (
            self.is_variable
            or self.is_ignorable
            or self == other
        )

    @property
    def is_variable(self) -> bool:
        return self.value == "X"

    @property
    def is_ignorable(self) -> bool:
        return self.value is None or self.value == "nb"


class Index:
    # easy-to-read unique identifier for each object created
    __next_id = 100

    def __init__(self):
        self.value = Index.__next_id
        Index.__next_id += 1

    def __str__(self) -> str:
        return str(self.value)


class Category(object):
    @property
    def is_functor(self) -> bool:
        return not self.is_atomic

    @property
    def is_atomic(self) -> bool:
        return not self.is_functor

    @property
    def is_variable(self) -> bool:
        if isinstance(self, VariableCategory):
            return True
        return False

    def __repr__(self) -> str:
        return str(self)

    def __truediv__(self, other: 'Category') -> 'Category':
        return Functor(self, '/', other)

    def __or__(self, other: 'Category') -> 'Category':
        return Functor(self, '\\', other)

    @classmethod
    def parse(cls, text: str) -> 'Category':
        tokens = cat_split.sub(r' \1 ', text)
        buffer = list(reversed([i for i in tokens.split(' ') if i != '']))
        stack = []

        while len(buffer):
            item = buffer.pop()
            if item in punctuations:
                stack.append(Atom(item))
            elif item in '(<':
                pass
            elif item in ')>':
                y = stack.pop()
                if len(stack) == 0:
                    return y
                f = stack.pop()
                x = stack.pop()
                stack.append(Functor(x, f, y))
            elif item in '/\\|':
                stack.append(item)
            else:
                if len(buffer) >= 3 and buffer[-1] == '[':
                    buffer.pop()
                    feature = Feature.parse(buffer.pop())
                    assert buffer.pop() == ']'
                    stack.append(Atom(item, feature))
                else:
                    stack.append(Atom(item))

        if len(stack) == 1:
            return stack[0]
        try:
            x, f, y = stack
            return Functor(x, f, y)
        except ValueError:
            raise RuntimeError(f'failed to parse category: {text}')


@dataclass(frozen=False, repr=False, unsafe_hash=True)
class Atom(Category):

    def __init__(self, base: str, feature: Feature = None):
        self.base = base
        if feature is None:
            self.feature = UnaryFeature()
        else:
            self.feature = feature
        self.index = Index()

    def __str__(self) -> str:
        feature = str(self.feature)
        if len(feature) == 0:
            return self.base
        return f'{self.base}[{feature}]'

    def to_str(self) -> str:
        feature = str(self.feature)
        if len(feature) == 0:
            return f'{self.base}{{{self.index}}}'
        return f'{self.base}[{feature}]{{{self.index}}}'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return str(self) == other
        elif not isinstance(other, Atom):
            return False
        return (
            self.base == other.base
            and self.feature == other.feature
        )

    def __xor__(self, other: object) -> bool:
        if not isinstance(other, Atom):
            return False
        return self.base == other.base

    @property
    def is_atomic(self) -> bool:
        return True

    @property
    def nargs(self) -> int:
        return 0

    def arg(self, index: int) -> Optional[Category]:
        if index == 0:
            return self
        return None

    def clear_features(self, *args) -> 'Atom':
        if self.feature in args:
            return Atom(self.base)
        return self


@dataclass(frozen=False, repr=False, unsafe_hash=True)
class Functor(Category):

    def __init__(self, left: Category, slash: str, right: Category):
        self.left = left
        self.slash = slash
        self.right = right
        self.index = Index()

    def __str__(self) -> str:
        def _str(cat):
            if isinstance(cat, Functor):
                return f'({cat})'
            return str(cat)
        return _str(self.left) + self.slash + _str(self.right)

    def to_str(self) -> str:
        return f'({self.left.to_str()}{self.slash}{self.right.to_str()}){{{self.index}}}'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return str(self) == other
        elif not isinstance(other, Functor):
            return False
        return (
            self.left == other.left
            and self.slash == other.slash
            and self.right == other.right
        )

    def __xor__(self, other: object) -> bool:
        if not isinstance(other, Functor):
            return False
        return (
            self.left ^ other.left
            and self.slash == other.slash
            and self.right ^ other.right
        )

    @property
    def functor(self) -> Callable[[Category, Category], Category]:
        return lambda x, y: Functor(x, self.slash, y)

    @property
    def is_functor(self) -> bool:
        return True

    @property
    def nargs(self) -> int:
        return 1 + self.left.nargs

    def arg(self, index: int) -> Optional[Category]:
        if self.nargs == index:
            return self
        else:
            return self.left.arg(index)

    def clear_features(self, *args) -> Category:
        return self.functor(
            self.left.clear_features(*args),
            self.right.clear_features(*args)
        )


@dataclass(frozen=False, repr=False)
class VariableCategory(Category):
    # easy-to-read unique identifier for each object created
    __next_id = 0

    def __init__(self):
        self.id = VariableCategory.__next_id
        self.index = Index()
        VariableCategory.__next_id += 1

    def __str__(self) -> str:
        return f'X_{self.id}'

    def to_str(self) -> str:
        return f'X_{self.id}{{{self.index}}}'

    @property
    def is_variable(self) -> bool:
        return True

    def update(self, cat: Category, keep_index=True):
        old_index = self.index
        self.__dict__.clear()
        self.__dict__.update(cat.__dict__)
        self.__class__ = cat.__class__
        if keep_index:
            self.index = old_index


def apply_default_slash_direction(cat, default_slash):
    if isinstance(cat, Functor):
        if cat.slash == '|':
            cat.slash = default_slash
        apply_default_slash_direction(cat.left, default_slash)
        apply_default_slash_direction(cat.right, default_slash)


# this function is intended for nsubj/obj/iobj, which uses default conversion rule (see rules.py)
# since the dependent tends to be nominal, set the default category to NP
def apply_default_category(cat, default_cat=Category.parse('NP')):
    if cat is not None:
        if cat.is_variable:
            cat.update(default_cat)

        if isinstance(cat, Functor):
            apply_default_category(cat.left)
            apply_default_category(cat.right)
