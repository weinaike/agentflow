import os
import clang.cindex
import pickle
import json
from typing import Union, List

class AST:    

    find_definition_description = '''
通过C++代码的抽象语法树，查找函数或变量的定义。
例如：
若需要查询函数PhotonArray::addTo的定义, 符号为'addTo', 其所属类为'PhotonArray'：
因而调用方式为
find_definition("addTo", "PhotonArray")
'''

    find_declaration_description = '''
通过C++代码的抽象语法树，查询函数或者变量的声明。如果查询声明未找到结果，可直接查询定义替代。
例如：
若需要查询函数Bounds的声明, 符号为'Bounds'：
因而调用方式为
find_declaration("Bounds")
'''


    def __init__(self, src_dir:str, include_dir:list, namespaces = ['galsim'], cache_file = 'symbol_table.pkl', load = True):
        self.directory = src_dir
        self.include = include_dir
        self.filter_namespaces = namespaces
        self.index = clang.cindex.Index.create()
        self.symbol_table = {}
        self.cache_file = cache_file
        if load:
            # Serialize the symbol table
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    self.symbol_table = pickle.load(f)
            else:
                self.source_files = self.get_source_files(self.directory)
                # for file in self.include:
                #     self.source_files += self.get_source_files(file)
                self.symbol_table = self.build_symbol_table(self.source_files)
                with open(cache_file, 'wb') as f:
                    pickle.dump(self.symbol_table, f)
        else:
            self.source_files = self.get_source_files(self.directory)
            # for file in self.include:
            #     self.source_files += self.get_source_files(file)
            self.symbol_table = self.build_symbol_table(self.source_files)

            with open(cache_file, 'wb') as f:
                pickle.dump(self.symbol_table, f)


    def get_source_files(self, directory):
        source_files = []
        # print(directory)
        for root, _, files in os.walk(directory):
            print(files)
            for file in files:
                if file.endswith(('.cpp', '.c','.h', '.hpp', '.cu', '.cc', '.cxx', '.cuh')):
                    source_files.append(os.path.join(root, file))
                    
        return source_files

    def parse_source_file(self, index, file):
        args = ['-x', 'c++', '--std=c++11']  # Adjust according to your project
        for include in self.include:
            args.append('-I'+include)
        translation_unit = index.parse(file, args=args)
        return translation_unit

    def visit_node(self, node: clang.cindex.Cursor, symbol_table):   
        if node.kind.is_declaration():
            symbol_name = node.spelling

            symbol_location = node.location
            if symbol_name not in symbol_table:
                symbol_table[symbol_name] = []

            extent = node.extent
            extent_start = extent.start.line
            extent_end = extent.end.line
            
            parent = node.semantic_parent
            parent_name = parent.spelling if parent else None

            is_definition = node.is_definition()

            content = (symbol_location.file.name, extent_start, extent_end, parent_name, is_definition )
            if content not in symbol_table[symbol_name]:
                symbol_table[symbol_name].append(content)

        for child in node.get_children():
            self.visit_node(child, symbol_table)


    def traverse(self, node: clang.cindex.Cursor, symbol_table: dict):
        if not node.kind.is_invalid():
            if node.kind == clang.cindex.CursorKind.NAMESPACE:
                if node.spelling in self.filter_namespaces:
                    self.visit_node(node, symbol_table) # forward to the previous function

        for child in node.get_children():
            self.traverse(child, symbol_table)

    def build_symbol_table(self, source_files):
        symbol_table = {}
        for file in source_files:
            translation_unit = self.parse_source_file(self.index, file)
            # print(f'Parsing {file}')
            for node in translation_unit.cursor.get_children():
                self.traverse(node, symbol_table)
        return symbol_table
    
    def get_text(self, param:list):
        file = param[0]
        start = param[1]
        end = param[2]
        text = ''
        with open(file, 'r') as f:
            lines = f.readlines()
            text = ''.join(lines[start-1:end])
        return text

    def update_symbol_table(self, file: Union[str, List[str]]):
        if isinstance(file, str):
            file_list = [file]
        elif isinstance(file, list):
            file_list = file
            
        for filename in file_list:
            # Step 1: Clear existing entries for the file
            keys_to_delete = []
            for symbol_name, contents in self.symbol_table.items():
                self.symbol_table[symbol_name] = [content for content in contents if content[0] != filename]
                if not self.symbol_table[symbol_name]:
                    keys_to_delete.append(symbol_name)
            for key in keys_to_delete:
                del self.symbol_table[key]

            # Step 2: Reparse the file and update the symbol table
            translation_unit = self.parse_source_file(self.index, filename)
            for node in translation_unit.cursor.get_children():
                self.traverse(node, self.symbol_table)
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.symbol_table, f)


    # Find the definition of a symbol
    def find_definition(self, symbol:str, class_name:str = None):
        definitions = []
        if symbol in self.symbol_table:        
            items =  self.symbol_table[symbol]  # Return the first definition found
            for item in items:
                is_definition = item[4]
                if not is_definition:
                    continue

                if class_name is None or class_name == '':
                    definitions.append(item)
                else:
                    if item[3] == class_name:
                        definitions.append(item)              
        key = symbol
        contents = {}
        if class_name == None or class_name == '':
            key = f"definition of {symbol}"
            contents[key] = list()
        else:
            key = f"definition of {class_name}::{symbol}"
            contents[key] = list()
       
        for defi in definitions:
            temp = dict()
            temp['file'] = defi[0]
            temp['start_line'] = defi[1]
            temp['end_line'] = defi[2]
            temp['text'] = self.get_text(defi)
            temp['is_definition'] = defi[4]
            temp['parent'] = defi[3]

            contents[key].append(temp)
        if len(contents[key]) == 0:
            return self.find_declaration(symbol, class_name)
        return json.dumps(contents)
    # Find the declaration of a symbol
   
    def find_declaration(self, symbol:str, class_name:str = None):
        declarations = []
        if symbol in self.symbol_table:        
            items =  self.symbol_table[symbol]  # Return the first definition found
            for item in items:               
                is_definition = item[4]

                if is_definition:
                    continue

                if class_name is None or class_name == '':
                    declarations.append(item)
                else:
                    if item[3] == class_name:
                        declarations.append(item)            
        # print(len(declarations))
        key = symbol
        contents = {}
        if class_name == None or class_name == '':
            key = f"declarations of {symbol}"
            contents[key] = list()
        else:
            key = f"declarations of {class_name}::{symbol}"
            contents[key] = list()
        
        for decl in declarations:
            temp = dict()
            temp['file'] = decl[0]
            temp['start_line'] = decl[1]
            temp['end_line'] = decl[2]
            temp['text'] = self.get_text(decl)
            temp['is_definition'] = decl[4]
            temp['parent'] = decl[3]
            contents[key].append(temp)
        
        if len(contents[key]) == 0:
            return self.find_definition(symbol, class_name)

        return json.dumps(contents)


if __name__ == "__main__":
    src = '/home/wnk/code/GalSim/src'  # Change this to the path of your source code directory
    include = ['/home/wnk/code/GalSim/include/galsim/']  # Change this to the path of your include directory
    namespaces=['galsim']
    cache_file = 'symbol_table.pkl'

    ast = AST(src, include, namespaces, cache_file, load = True)

    
    symbol_to_find = 'shoot'  # Change this to the symbol you want to find
    class_name = 'SBTopHatImpl'  # Change this to the class name if the symbol is a member function or variable
    
    rets = ast.find_definition(symbol_to_find, class_name)
    print('def',rets)
    # for ret, txt in rets.items():
    #     print('def',ret, txt)
    rets = ast.find_declaration(symbol_to_find, class_name)
    print('decl',rets)





