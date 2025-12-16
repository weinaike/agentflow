from enum import Enum, unique
from abc import abstractmethod

@unique
class SupportedLang(Enum):
    PYTHON = 1    
    C = 2
    FORTRAN = 3

class ParserBase:
    def parse(self, filename, **kwargs): 
        '''
        Parse the given file and return the corresponding syntax tree.
        
        :param self: the parser instance
        :param filename: The path to the source file to be parsed
        :param kwargs: type-specific arguments for parsing
        :return: The syntax tree representation of the parsed file
        :rtype: TSTree | TranslationUnit | ...
        '''
        pass