from clang.cindex import Index, TranslationUnit, Cursor
from tree_sitter import Tree, Node

from typing import List, Union
from enum import Enum, unique
from abc import abstractmethod

@unique
class SupportedLang(Enum):
    PYTHON = 1    
    C = 2
    FORTRAN = 3

class TSTree:
    def __init__(self, tree: Tree, filename: str):
        self.tree = tree
        self.filename = filename

class TSNode:
    def __init__(self, spelling: str, node: Node=None, ts_tree: TSTree=None):
        '''
        for a reference node, only spelling is set
        '''
        self.spelling = spelling
        self.node = node
        self.ts_tree = ts_tree

class ParserBase:
    @abstractmethod
    def parse(self, filename, *, index: Union[None, Index]=None, args={}) -> Union[TSTree, TranslationUnit]:
        pass