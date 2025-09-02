import magic
import os
from pathlib import Path
from typing import List, Union
from abc import ABC, abstractmethod

from tree_sitter import Language, Parser, Tree, Node, Query, QueryCursor

import tree_sitter_c as ts_c
import tree_sitter_python as ts_python
import tree_sitter_fortran as ts_fortran

from clang.cindex import Index, TranslationUnit, Cursor

from enum import Enum, unique

from AgentFlow.tools.language_config import LANGUAGE_CONFIGS, LanguageConfig
from AgentFlow.tools.parser_base import ParserBase

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

def load_parsers() -> tuple[dict[str, Parser], dict[str, Any]]:
    """Loads all available Tree-sitter parsers and compiles their queries."""
    parsers: dict[str, Parser] = {}
    queries: dict[str, Any] = {}
    available_languages = []

    for lang_name, lang_config in LANGUAGE_CONFIGS.items():
        if lang_lib := LANGUAGE_LIBRARIES.get(lang_name):
            try:
                language = Language(lang_lib())
                parser = Parser(language)

                parsers[lang_name] = parser

                # Compile queries
                function_patterns = " ".join(
                    [
                        f"({node_type}) @function"
                        for node_type in lang_config.function_node_types
                    ]
                )
                class_patterns = " ".join(
                    [
                        f"({node_type}) @class"
                        for node_type in lang_config.class_node_types
                    ]
                )
                call_patterns = " ".join(
                    [
                        f"({node_type}) @call"
                        for node_type in lang_config.call_node_types
                    ]
                )

                # Create import query patterns
                import_patterns = " ".join(
                    [
                        f"({node_type}) @import"
                        for node_type in lang_config.import_node_types
                    ]
                )
                import_from_patterns = " ".join(
                    [
                        f"({node_type}) @import_from"
                        for node_type in lang_config.import_from_node_types
                    ]
                )

                # Combine import patterns (remove duplicates)
                all_import_patterns = []
                if import_patterns.strip():
                    all_import_patterns.append(import_patterns)
                if (
                    import_from_patterns.strip()
                    and import_from_patterns != import_patterns
                ):
                    all_import_patterns.append(import_from_patterns)
                combined_import_patterns = " ".join(all_import_patterns)

                queries[lang_name] = {
                    "functions": Query(language, function_patterns),
                    "classes": Query(language, class_patterns),
                    "calls": Query(language, call_patterns) if call_patterns else None,
                    "imports": Query(language, combined_import_patterns)
                    if combined_import_patterns
                    else None,
                    "config": lang_config,
                }

                available_languages.append(lang_name)
                logger.success(f"Successfully loaded {lang_name} grammar.")
            except Exception as e:
                logger.warning(f"Failed to load {lang_name} grammar: {e}")
        else:
            logger.debug(f"Tree-sitter library for {lang_name} not available.")

    if not available_languages:
        raise RuntimeError("No Tree-sitter languages available.")

    logger.info(f"Initialized parsers for: {', '.join(available_languages)}")
    return parsers, queries

class TreeSitterParser(ParserBase):
    def __init__(self, lang: SupportedLang):
        if lang == SupportedLang.PYTHON:
            self.lang = Language(ts_python.language())
        elif lang == SupportedLang.C:
            self.lang = Language(ts_c.language())    
        elif lang == SupportedLang.FORTRAN:
            self.lang = Language(ts_fortran.language())    
        else:
            raise ValueError("Language unsupported!")    
        # TODO: add other language parsers

        self.parser = Parser(self.lang)

    def parse(self, filename, *, index=None, args={}) -> Union[TSTree, TranslationUnit]:    
        with open(filename, 'r', encoding='utf-8') as file:
            code = file.read()
        tree = self.parser.parse(bytes(code, "utf-8"))  # tree_sitter.Tree  
        return TSTree(tree, os.path.abspath(filename))

    def get_call_expr_nodes(self, node: Union[TSNode, Cursor], filters=[], unique=False, sort=False) -> Union[List[TSNode], List[Cursor]]:
        call_exprs = []
        
        def traverse(node: Node):
            if node.type == 'call':
                target = node.children[0]
                if target.type in ('attribute', 'identifier'):
                    call_exprs.append(target.text.decode())
            
            # 递归遍历子节点
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return call_exprs

    def get_call_expr_nodes(self, node: Union[TSNode, Cursor], filters=[], unique=False, sort=False) -> Union[List[TSNode], List[Cursor]]:
        call_exprs = []
        lang = node.ts_tree.tree.language # TODO: for Fortran AST, the language is None ...
        if lang == "python":
            query = """"""
        elif lang == "c":
            query = """
            """
        elif lang == None:
            query = """
            """        
        return call_exprs

    def get_symbols(self, node, source_code, current_class=None):
        symbols = []

        if node.type == 'class_definition':
            class_node = node.child_by_field_name('name')
            class_name = source_code[class_node.start_byte:class_node.end_byte].decode()
            for child in node.children:
                if child.type == 'block':
                    symbols.extend(self.get_symbols(child, source_code, class_name))
        elif node.type == 'function_definition':
            name_node = node.child_by_field_name('name')
            method_name = source_code[name_node.start_byte:name_node.end_byte].decode()
            symbols.append({
                'name': f"{current_class}.{method_name}" if current_class else method_name,
                'type': 'class_method' if current_class else 'function',
                'location': (node.start_point[0]+1, node.end_point[0] + 1)
            })           
                
        for child in node.children:
            symbols.extend(self.get_symbols(child, source_code, current_class))        

        return symbols    
    
    def get_symbol_definition_by_name(self, tu: Union[TSTree, TranslationUnit], symbol: str, type=None)->Union[List[TSNode], List[Cursor]]:
        '''
        TODO: use xpath query to speedup
        '''
        defs = []
        root_node = tu.tree.root_node
        def get_def_recursively(node: Node, symbol:str, defs):
            if node.type == 'function_definition':
                for child in node.children:
                    if child.type == 'identifier':
                        if child.text.decode("utf-8") == symbol:
                            defs.append(TSNode(spelling=symbol, node=node, ts_tree=tu.tree))
                            return
            for child in node.children:
                get_def_recursively(child, symbol, defs)
                                
        get_def_recursively(root_node, symbol, defs)
        return defs                

    def get_symbol_declaration_by_name(self, tu, symbol, type=None):
        pass 

    def traverse_tree(self, ts_tree: TSTree, visitor=None):
        root_node = ts_tree.tree.root_node
        count = 0
        
        def _traverse(node, depth=0):
            nonlocal count 
            count += 1
            if visitor is not None:
                result = visitor(node, depth)
                if result is False:
                    return
                
            for child in node.children:
                _traverse(child, depth + 1)    
        
        _traverse(root_node)
        return count        
        
        
    
class ClangParser(ParserBase):
    def __init__(self):
        pass

    def get_include_headers(self, filename, index=None, args={}):
        index = index or Index.create()
        tu = index.parse(filename, args=args, options=TranslationUnit.PARSE_SKIP_FUNCTION_BODIES|TranslationUnit.PARSE_INCOMPLETE)
        header_files = set([include.include.name for include in tu.get_includes()])
        return header_files

    def parse(self, filename, *, index=None, args={}):
        if index:
            options = TranslationUnit.PARSE_PRECOMPILED_PREAMBLE
        else:
            options = 0
            index = Index.create()    
        tu = index.parse(filename, args=args, options=options)    
        return tu

    def extract_symbols(self, tu, filters=[]):
        pass    
            

class ProjectBase:
    def __init__(self, config):
        self.config = config
        self.translation_units = {}
        self.classes = {}
        self.symbols_def = {}
        self.symbols_decl = {}

    def find_definition():
        pass
    
    def find_declaration():
        pass
    
    def fetch_source_code():
        pass    

class Project(ProjectBase):
    pass

class CppProject(ProjectBase):
    def __init__(self, 
                 build_options: List[str]=[], 
                 force_build: bool = False,
                 build_dir: str = None,
                 src_dirs: List[str]=[], 
                 filter_by_dirs: List[str]=[], filter_by_namespaces: List[str]=[]
    ):
        self.build_options = build_options
        self.force_build = force_build
        self.build_dir = build_dir
        self.src_dirs = src_dirs
        self.filter_by_dirs = filter_by_dirs
        self.filter_by_namespaces = filter_by_namespaces
        self.index = Index()
        self.parser = ClangParser()

        self.translation_units = {}
        self.symbols_defs = {}
        self.symbols_decls = {}

        self.parse()

    def need_build(self, source_file):
        if self.force_build or self.build_dir is None:
            return True

        ast_file = os.path.join(self.build_dir, source_file + ".ast")
        if not os.path.exists(ast_file):
            return True

        last_build_time, last_modified_time = os.path.getmtime(ast_file), os.path.getmtime(source_file)    
        if last_modified_time > last_build_time:
            return True

        include_header_files = self.parser.get_include_headers(source_file, self.index, self.build_options)    
        for include_header_file in include_header_files:
            if os.path.getmtime(include_header_file) > last_modified_time:
                return True

        return False        

            
    
    def list_source_files(self) -> List[str]:
        pass

    def parse(self):
        for source_file in self.list_source_files():
            ast_file = os.path.join(self.build_dir, source_file + ".ast")
            if not self.need_build(source_file):
                if not source_file in self.translation_units.keys():
                    self.translation_units[source_file] = self.index.read(ast_file)
            else:
                tu = self.parser.parse(filename=source_file, index=self.index, args=self.build_options)
                self.translation_units[source_file] = tu
                if self.build_dir:
                    os.makedirs(os.path.dirname(ast_file), exist_ok=True)
                    tu.save(ast_file)
            
    def extract_symbols(self):        
        self.symbols_defs = {}
        self.symbols_decls = {}
        self.classes = {}
        self.parse()

        

    def find_definition(self, symbol, type=None, requires_lines=True):    
        pass

    def find_declaration(self, symbol, type=None):
        pass

    def fetch_source_code(self, symbol, type=None, requires_lines=True, requires_classes=True, requires_complete_target_files: Union[None, List[str]]=[]):
        pass

    



def TEST_TreeSitterParser_get_call_expr_nodes():
    parser = TreeSitterParser(SupportedLang.PYTHON)
    filename = "/home/jiangbo/GalSim/tests/test_shear_position.py"
    tree = parser.parse(filename=filename)
    #node = parser.get_symbol_definition_by_name(translation_unit, "test_shear_position_image_integration_offsetwcs")
    with open(filename, "rb") as f:
        source_code = f.read()
    symbols = parser.get_symbols(tree.root_node, source_code, None)
    print(symbols)

def TEST_TreeSitterParser_get_definition_by_name():
    parser = TreeSitterParser(SupportedLang.PYTHON)
    filename = "/home/jiangbo/GalSim/tests/test_shear_position.py"
    tree = parser.parse(filename=filename)
    defs = parser.get_symbol_definition_by_name(tree, symbol="test_shear_position")
    print(defs)

def TEST_PYTHON_traverse_tree():
    parser = TreeSitterParser(SupportedLang.PYTHON)
    filename = "/home/jiangbo/tmp/tree-sitter/mytest.py"
    tree = parser.parse(filename=filename)
    def print_node_info(node: Node, depth):
        indent = "  " * depth
        node_text = node.text.decode('utf-8')[:50].replace('\n', '\\n')
        print(f"{depth:02d}:   {indent}{node.type}: {node.start_point.row}~{node.end_point.row} {node_text}")
    parser.traverse_tree(tree, print_node_info)

def TEST_C_traverse_tree():
    parser = TreeSitterParser(SupportedLang.C)
    filename = "/home/jiangbo/tmp/tree-sitter/C/person.h"
    tree = parser.parse(filename=filename)
    def print_node_info(node: Node, depth):
        indent = "  " * depth
        node_text = node.text.decode('utf-8')[:50].replace('\n', '\\n')
        print(f"{depth:02d}:   {indent}{node.type}: {node.start_point.row}~{node.end_point.row} {node_text}")
    parser.traverse_tree(tree, print_node_info)

def TEST_FORTRAN_traverse_tree():
    parser = TreeSitterParser(SupportedLang.FORTRAN)
    #filename = "/home/jiangbo/tmp/tree-sitter/FORTRAN/complete.f90"
    filename = "/home/jiangbo/tmp/tree-sitter/FORTRAN/student.f90"
    tree = parser.parse(filename=filename)
    def print_node_info(node: Node, depth):
        indent = "  " * depth
        node_text = node.text.decode('utf-8')[:50].replace('\n', '\\n')
        print(f"{depth:02d}:   {indent}{node.type}: {node.start_point.row}~{node.end_point.row} {node_text}")
    parser.traverse_tree(tree, print_node_info)

def get_all_function(tree: Tree) -> list:
    # 获取语言类型
    language = tree.language.name
    
    # 定义查询模式
    if language == "python":  # Python
        query_code = """
        (function_definition) @function
        """
    elif language == "c":  # C
        query_code = """
        (function_definition) @function
        """
    elif language == "fortran":
        query_code = """
        (function_definition) @function
        (subroutine_definition) @function
        """
    else:
        query_code = """
        (function) @function
        (program) @function
        (subroutine) @function
        """
    
    # 创建查询对象
    #query = tree.language.query(query_code)
    query = Query(tree.language, query_code)
    
    # 创建查询游标
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    functions = captures['function']
    
    return functions

def TEST_C_get():
    parser = TreeSitterParser(SupportedLang.C)
    filename = "/home/jiangbo/tmp/tree-sitter/C/person.c"
    tree = parser.parse(filename=filename)

    print(get_all_function(tree.tree))

def TEST_PYTHON_get():
    parser = TreeSitterParser(SupportedLang.PYTHON)
    filename = "/home/jiangbo/tmp/tree-sitter/PYTHON/mytest.py"
    tree = parser.parse(filename=filename)

    print(get_all_function(tree.tree))

def TEST_FORTRAN_get():
    parser = TreeSitterParser(SupportedLang.FORTRAN)
    #filename = "/home/jiangbo/tmp/tree-sitter/FORTRAN/complete.f90"
    filename = "/home/jiangbo/tmp/tree-sitter/FORTRAN/student.f90"
    tree = parser.parse(filename=filename)

    print(get_all_function(tree.tree))

if __name__ == '__main__':
    #TEST_TreeSitterParser_get_call_expr_nodes()
    #TEST_TreeSitterParser_get_definition_by_name()
    #TEST_PYTHON_traverse_tree()
    #TEST_FORTRAN_traverse_tree()

    #TEST_C_traverse_tree()
    TEST_FORTRAN_get()