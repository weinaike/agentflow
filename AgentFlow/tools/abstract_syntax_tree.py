import os
from clang.cindex import Cursor, CursorKind, TranslationUnit, Index, Diagnostic
import copy
import json
import time
import numpy as np
from typing import Union, List
from collections import deque

try:
    from .utils import thread_safe_singleton
except:
    import sys
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))    
    from utils import thread_safe_singleton


class CursorUtils:
    @staticmethod
    def is_class_definition(node):
        return node.is_definition() and node.kind in [CursorKind.CLASS_DECL,
            CursorKind.CLASS_TEMPLATE, CursorKind.STRUCT_DECL, 
            CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION]
    
    @staticmethod
    def is_callable(node):
        return CursorUtils.is_function(node) or CursorUtils.is_method(node)
    
    @staticmethod
    def is_function(node):
        return node.kind == CursorKind.FUNCTION_DECL or \
            (node.kind == CursorKind.FUNCTION_TEMPLATE and not CursorUtils.is_class_definition(node.semantic_parent)) 
    
    @staticmethod
    def is_method(node):
        return node.kind in [CursorKind.CXX_METHOD, CursorKind.CONSTRUCTOR] or \
            (node.kind ==  CursorKind.FUNCTION_TEMPLATE and CursorUtils.is_class_definition(node.semantic_parent))   
    
    @staticmethod
    def get_scope(node):
        parent = node.semantic_parent
        scope = ""
        while parent and parent.kind != CursorKind.TRANSLATION_UNIT:
            #TODO: use displayname instead of spelling?
            if parent.spelling == '':
                parent = parent.semantic_parent
                continue
            scope = parent.spelling if scope == "" else "::".join([parent.spelling, scope]) 
            parent = parent.semantic_parent
        return scope    
    
    @staticmethod
    def get_full_displayname(node):
        scope = CursorUtils.get_scope(node)
        full_displayname = "::".join([scope, node.displayname]) if scope else node.displayname
        return full_displayname
    
    @staticmethod
    def get_full_name(node):
        scope = CursorUtils.get_scope(node)
        full_name = "::".join([scope, node.spelling]) if scope else node.spelling
        return full_name
    
    @staticmethod
    def get_namespace(node: Cursor):
        parent: Cursor = node
        namespace = ""
        while parent and parent.kind not in [CursorKind.TRANSLATION_UNIT, CursorKind.NAMESPACE]:
            parent = parent.semantic_parent
        while parent.kind == CursorKind.NAMESPACE:
            namespace = parent.spelling if namespace == "" else "::".join([parent.spelling, namespace])    
            parent = parent.semantic_parent
        return namespace    
    
    @staticmethod
    def get_using_namespaces(node: Cursor):
        using_namespaces = []
        #tu = node.translation_unit if node.kind != CursorKind.TRANSLATION_UNIT else node
        using_directives = [child for child in node.get_children() if child.kind == CursorKind.USING_DIRECTIVE]
        for using_directive in using_directives:
            using_child = [child for child in using_directive.get_children()]
            if using_child and using_child[0].kind == CursorKind.NAMESPACE_REF:
                using_namespaces.add(using_child[0].spelling)
        return using_namespaces
    
    @staticmethod
    def get_class_methods(node):
        assert CursorUtils.is_class_definition(node), "Only class nodes have methods"
        method_nodes = [c for c in node.get_children() if CursorUtils.is_method(c)]
        return method_nodes   
    
    @staticmethod
    def get_functions(node):
        #assert node.kind == CursorKind.NAMESPACE
        function_nodes = [c for c in node.get_children() if CursorUtils.is_method(c) or CursorUtils.is_function(c)]
        return function_nodes
    
    @staticmethod
    def get_inner_classes(node):    
        def _get_inner_class_recursively(node):
            assert CursorUtils.is_class_definition(node), "Only class nodes have inner classes"
            inner_classes = [c for c in node.get_children() if CursorUtils.is_class_definition(c)]
            return inner_classes
        all_inner_classes = []    
        task_queue = deque([node])
        while task_queue:
            node = task_queue.popleft()
            inner_classes = _get_inner_class_recursively(node)
            all_inner_classes.extend(inner_classes)
            task_queue.extend(inner_classes)
        return all_inner_classes    

class CallGraph:
    def __init__(self, node: Cursor, parent: 'CallGraph'=None):
        self.node = node
        self.parent = parent
        self.has_circle = False
        self.subgraphs = []

    def add_subgraph(self, subgraph:'CallGraph'):
        parent = subgraph.parent
        has_circle = False
        while parent:
            if parent.node.get_usr() == subgraph.node.get_usr():
                has_circle = True
                break
            parent = parent.parent
        self.subgraphs.append(subgraph)    
        subgraph.has_circle = has_circle

    def add_subgraphs(self, subgraphs):
        for subgraph in subgraphs:
            self.add_subgraph(subgraph)    

    def to_dict_v0(self):
        res = {}
        node_name = CursorUtils.get_full_name(self.node)
        res[node_name] = []
        for subgraph in self.subgraphs:
            subres = subgraph.to_dict_v0()
            res[node_name].append(subres)

        return res    

    def to_dict(self, requires_signature=False):
        res = {}    
        queue = deque([self])
        while queue:
            graph = queue.popleft()
            node_name = CursorUtils.get_full_displayname(graph.node) if requires_signature else CursorUtils.get_full_name(graph.node)
            if node_name not in res.keys():
                res[node_name] = [CursorUtils.get_full_displayname(subgraph.node) if requires_signature else \
                    CursorUtils.get_full_name(subgraph.node) for subgraph in graph.subgraphs]
            queue.extend(graph.subgraphs)
        return res    

    def to_string(self, remove_leaf_nodes=True, requires_signature=False):
        res = {}    
        queue = deque([self])
        while queue:
            graph = queue.popleft()
            node_name = CursorUtils.get_full_displayname(graph.node) if requires_signature else CursorUtils.get_full_name(graph.node)
            if node_name not in res.keys():
                depends  = [CursorUtils.get_full_displayname(subgraph.node) if requires_signature else \
                    CursorUtils.get_full_name(subgraph.node) for subgraph in graph.subgraphs]
                count = len(depends)
                if count > 0 or not remove_leaf_nodes:
                    depends = [f"`{node}`" for node in depends]    
                    depends = ', '.join(depends)
                    res[node_name] = "调用了如下函数/方法：%s" % depends if count > 0 else "没有调用其它函数/方法"
            queue.extend(graph.subgraphs)
        return json.dumps(res, ensure_ascii=False)    

    def draw_callgraph(self):
        groups_by_class = {}
        groups_by_file = {}
        queue = deque([self])
        while queue:
            graph = queue.popleft()
            if CursorUtils.is_class_definition(graph.node.semantic_parent):
                key = CursorUtils.get_full_name(graph.node.semantic_parent)
                group = groups_by_class.get(key, None)
                if group:
                    group.append(graph.node)
                else:
                    groups_by_class[key] = [graph.node]
            else:
                key = graph.node.location.file.name        
                group = groups_by_file.get(key, None)
                if group:
                    group.append(graph.node)
                else:
                    groups_by_file[key] = [graph.node]    
            queue.extend(graph.subgraphs)        

        print(f"{len(groups_by_class)}; {len(groups_by_file)}")    
        for key, value in groups_by_class.items():
            print(f"{key}: {len(value)}")
        print("========================")
        for key, value in groups_by_file.items():
            print(f"{key}: {len(value)}")

class TuSymbolTable:
    def __init__(self, tu: TranslationUnit, parsing_filters=[]):
        self.tu = tu
        self.parsing_filters = parsing_filters
        self.def_cursors = dict()
        self.decl_cursors = dict()
        # self.classes仅用于查找类的定义，不是符号表的一部分
        self.classes = dict()
        # self.local_cursors只记录在当前文件(不包含include文件)中定义的各个节点
        self.local_cursors = []

        self.extract_symbols()

    def extract_symbols(self):
        self.def_cursors, self.decl_cursors = dict(), dict()
        self.classes = dict()
        self.local_cursors = []
        task_queue = deque([self.tu.cursor])
        while task_queue:
            node = task_queue.popleft()

            namespace_nodes = [child for child in node.get_children() if child.kind == CursorKind.NAMESPACE]
            task_queue.extend(namespace_nodes)
            self.local_cursors.extend([node for node in namespace_nodes if node.location.file.name == self.tu.spelling])

            ## add symbols in the current `node`
            #(1) 提取变量符号
            variable_nodes = [child for child in node.get_children() if child.kind == CursorKind.VAR_DECL]
            self.local_cursors.extend([node for node in variable_nodes if node.location.file.name == self.tu.spelling])
            self.add_declarations(variable_nodes)
            self.add_definitions(variable_nodes)
            #(2) 提取在类内声明/定义的方法符号
            class_nodes = [child for child in node.get_children() if CursorUtils.is_class_definition(child)]
            inner_class_nodes = []
            for class_node in class_nodes:
                inner_class_nodes.extend(CursorUtils.get_inner_classes(class_node))
            class_nodes.extend(inner_class_nodes)    
            self.local_cursors.extend([node for node in class_nodes if node.location.file.name == self.tu.spelling])
            self.add_classes(class_nodes)
            for class_node in class_nodes:
                method_nodes = CursorUtils.get_class_methods(class_node)
                self.local_cursors.extend([node for node in method_nodes if node.location.file.name == self.tu.spelling])
                self.add_declarations(method_nodes)
                self.add_definitions(method_nodes)
            #(3) 函数、类外方法符号
            func_nodes = CursorUtils.get_functions(node)
            self.local_cursors.extend([node for node in func_nodes if node.location.file.name == self.tu.spelling])
            self.add_declarations(func_nodes)
            self.add_definitions(func_nodes)

    def add_declarations(self, cursors):
        if not isinstance(cursors, list):
            cursors = [cursors]
        cursors = [cursor for cursor in cursors if not cursor.is_definition()]
        for cursor in cursors:
            discard = False
            for parsing_filter in self.parsing_filters:
                if parsing_filter(cursor):
                    discard = True
                    break
            if not discard:
                self.decl_cursors[cursor.get_usr()] = cursor

    def add_definitions(self, cursors):
        if not isinstance(cursors, list):    
            cursors = [cursors]
        cursors = [cursor for cursor in cursors if cursor.is_definition()]
        for cursor in cursors:
            discard = False
            for parsing_filter in self.parsing_filters:
                if parsing_filter(cursor):
                    discard = True
                    break
            if not discard:
                self.def_cursors[cursor.get_usr()] = cursor

    def add_classes(self, classes):
        if not isinstance(classes, list):    
            classes = [classes]
        classes = [clazz for clazz in classes if clazz.is_definition()]
        for clazz in classes:
            discard = False
            for parsing_filter in self.parsing_filters:
                if parsing_filter(clazz):
                    discard = True
                    break
            if not discard:
                #self.classes.add(clazz)
                self.classes[clazz.get_usr()] = clazz

    def find_definition_by_cursor(self, decl_cursor: Cursor):
        if decl_cursor.is_definition():
            return decl_cursor
        usr = decl_cursor.get_usr()
        return self.def_cursors.get(usr, None)            

    def find_declaration_by_cursor(self, def_cursor: Cursor):
        usr = def_cursor.get_usr()
        return self.decl_cursors.get(usr, None)

    def find_definition_by_name(self, name, scope=None, type=None):
        defs = []
        for def_cursor in self.def_cursors.values():
            if def_cursor.spelling == name:
                cursor_scope = CursorUtils.get_scope(def_cursor)
                if scope is None or cursor_scope[-len(scope):] == scope:
                    if type is None or def_cursor.type.spelling == type:
                        defs.append(def_cursor)
        return defs                

    def find_declaration_by_name(self, name, scope=None, type=None):    
        decls = []
        for decl_cursor in self.decl_cursors.values():
            if decl_cursor.spelling == name:
                cursor_scope = CursorUtils.get_scope(decl_cursor)
                if scope is None or cursor_scope[-len(scope):] == scope:
                    if type is None or decl_cursor.type.spelling == type:
                        decls.append(decl_cursor)
        return decls

    def find_references_by_cursor(self, cursor):   
        refs = []
        usr = cursor.get_usr()
        for token in self.tu.cursor.get_tokens():
            if token.cursor.referenced.get_usr() == usr:
                refs.append(token.cursor)
        return refs        

    def find_context(self, line: int):
        context = self.tu.cursor
        range_start, range_end = context.extent.start.line, context.extent.end.line
        assert range_start <= line and line <= range_end
        for cursor in self.local_cursors:
            if cursor.extent.start.line < line and line <= cursor.extent.end.line:
                if cursor.extent.start.line > range_start and cursor.extent.end.line <= range_end:
                    range_start = cursor.extent.start.line
                    range_end = cursor.extent.end.line
                    context = cursor
        return context            

@thread_safe_singleton
class AST:    

    find_definition_description = '''
通过C++代码的抽象语法树，查找函数或类的定义。
例如：
若需要查询方法galsim::PhotonArray::addTo的定义, 只需要调用：
    find_definition("addTo", "galsim::PhotonArray")
但若需要查询galsim::PhotonArray类的定义，只需要将find_definition函数的第一个参数设为空即可，即调用：
    find_definition("", "galsim::PhotonArray")    
'''

    find_declaration_description = '''
通过C++代码的抽象语法树，查询函数或者变量的声明。如果查询声明未找到结果，可直接查询定义替代。
例如：
若需要查询方法galsim::PhotonArray::addTo的声明, 只需要调用：
    find_declaration("addTo", "galsim::PhotonArray")
'''

    def __init__(self):
        self.index_cxx_args = [
            '-std=c++14',
            '-xc++',
            '-DENABLE_CUDA',
            "-march=x86-64",
            #'-shared-libgcc',
            '-mtune=generic',
            "-target", "x86_64-linux-gnu",
            "-mavx",
            '-I/usr/local/cuda/include',

            #下面这句可以避免解析时出现这样的错误：error: use of undeclared identifier '__builtin_ia32_sbb_u64'
            '-I/usr/lib/llvm-15/lib/clang/15.0.7/include', 
            #'-I/home/jiangbo/llvm-project/install/lib/clang/20/include',

            "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"
        ]
        self.index_cuda_args = [
            '-std=c++14',
            '-xcuda',
            '-D__CUDA__',
            '-DENABLE_CUDA',
            '--cuda-gpu-arch=sm_60',
            '--cuda-path=/usr/local/cuda',
            '-Xclang', '-fno-cuda-host-device-constexpr',
            '-Xclang', '-fcuda-allow-variadic-functions',
            '-I/usr/local/cuda/include',

            '-I/usr/lib/llvm-15/lib/clang/15.0.7/include', 
            '-I/usr/lib/llvm-15/lib/clang/15.0.7/include/cuda_wrappers', 
            #'-I/home/jiangbo/llvm-project/install/lib/clang/20/include',
            #'-I/home/jiangbo/llvm-project/install/lib/clang/20/include/cuda_wrappers',

            "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/",
        ]
        self.cuda_src_directory = os.path.abspath("./cuda_kernels")

    def create_cache(self, src_dir:str, include_dir:list, *, namespaces=["galsim"], parsing_filters=[], cache_file='cached_ast_dir', load=True, cuda_src_dir=None):
        assert all([callable(filter) for filter in parsing_filters]), "filters must be callable!"
        self.directory = src_dir 
        self.include = include_dir
        if namespaces:
            self.parsing_filters = [
                lambda cursor:  CursorUtils.get_namespace(cursor) not in namespaces,
            ]
        else:    
            self.parsing_filters = parsing_filters
        self.index = Index.create()
        self.cuda_src_directory = os.path.abspath(cuda_src_dir or os.path.join(src_dir, "cuda_kernels"))
        self.tu_symbol_tables = {}
        self.tu_status = {}
        self.cache_dir = cache_file
        os.makedirs(self.cache_dir, exist_ok=True)
        
        print("正在解析源代码，请耐心等待……", flush=True)
        if load:
            self.load_symbol_tables()
        else:    
            self.build_symbol_tables()
        print("解析源代码完成", flush=True)

    def get_header_files(self, directory):
        header_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.h', '.hpp', '.cuh')):
                    header_files.append(os.path.abspath(os.path.join(root, file)))
                    
        return header_files

    def get_source_files(self, directory):
        source_files = []
        if os.path.isfile(directory):
            if directory.endswith(('.cpp', '.c', '.cc', '.cxx', '.cu')):
                source_files = [directory]
        else:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.cpp', '.c', '.cu', '.cc', '.cxx')):
                        source_files.append(os.path.abspath(os.path.join(root, file)))
                    
        return source_files

    def get_ast_files(self, file_names):
        directory = os.path.dirname(self.directory) if os.path.isfile(self.directory) else self.directory
        relpaths = [os.path.relpath(file_name, directory) for file_name in file_names]
        ast_files = [os.path.join(self.cache_dir, relpath + ".ast") for relpath in relpaths]
        return ast_files
            

    def parse_source_file(self, index: Index, file, options=0):
        args = copy.deepcopy(self.index_cxx_args) #不要修改原来的args
        if file.startswith(self.cuda_src_directory) or file.endswith(".cu"):
            args = copy.deepcopy(self.index_cuda_args)    

        for include in self.include:
            args.append('-I'+include)

        tu = index.parse(file, args=args, options=options)
        return tu

    def parse_virtual_file(self, index: Index, file, unsaved_files, options=TranslationUnit.PARSE_INCOMPLETE|TranslationUnit.PARSE_SKIP_FUNCTION_BODIES):
        args = copy.deepcopy(self.index_cxx_args) #不要修改原来的args
        if file.startswith(self.cuda_src_directory) or file.endswith(".cu"):
            args = copy.deepcopy(self.index_cuda_args)    

        for include in self.include:
            args.append('-I'+include)

        tu = index.parse(file, args=args, unsaved_files=unsaved_files, options=options)
        return tu


    def build_tu_symbol_table(self, source_file, ast_file, options=TranslationUnit.PARSE_PRECOMPILED_PREAMBLE):
        #print(f"{source_file}: building ...")
        st = time.time()

        #//TODO: 增量编译有时会出现如下的错误：
        # libclang: crash detected during reparsing
        # malloc(): unaligned tcache chunk detected
        #
        # 因此，先暂时关闭增量编译。若要开启，去掉if语句中的`and False`
        if source_file in self.tu_symbol_tables.keys() and False:
            symbol_table: TuSymbolTable = self.tu_symbol_tables[source_file]
            symbol_table.tu.reparse(None, options)
            symbol_table.extract_symbols()
        else:
            tu: TranslationUnit = self.parse_source_file(self.index, source_file, options)
            symbol_table = TuSymbolTable(tu, self.parsing_filters)

        build_success = True
        for diag in symbol_table.tu.diagnostics:
            if source_file.endswith((".cpp", ".cxx", ".cc")):
                #print(f"    {diag}")
                pass
            if diag.severity > Diagnostic.Warning: # Error or Fatal ...
                build_success = False
        et = time.time()
        #print(f"{source_file}: {'build successfully' if build_success else 'build failed'}. build cost: {et - st:6f}s\n")        

        if ast_file:
            if build_success:
                ast_dir = os.path.dirname(ast_file)
                if not os.path.exists(ast_dir):
                    os.makedirs(ast_dir)
                symbol_table.tu.save(ast_file)    
            else:
                if os.path.exists(ast_file):
                    os.remove(ast_file)    

        return build_success, symbol_table

    def load_tu_symbol_table(self, source_file, ast_file):
        #print(f"{source_file}: loading AST from {ast_file}")    
        tu: TranslationUnit = TranslationUnit.from_ast_file(ast_file)
        load_success = True
        for diag in tu.diagnostics:
            if source_file.endswith((".cpp", ".cxx", ".cc")):
                #print(f"    {diag}")
                pass
            if diag.severity > Diagnostic.Warning:
                load_success = False
        #if load_success:
        #    print(f"{source_file}: load AST successfully\n")        
        #else:
        #    print(f"{source_file}: load AST failed\n")    
        symbol_table = TuSymbolTable(tu, self.parsing_filters)    
        return load_success, symbol_table

    def build_symbol_tables(self):
        source_files = self.get_source_files(self.directory)
        ast_files = self.get_ast_files(source_files)
        for source_file, ast_file in zip(source_files, ast_files):
            ast_file = os.path.join(self.cache_dir, ast_file)
            _, symtable = self.build_tu_symbol_table(source_file, ast_file)
            self.tu_symbol_tables[source_file] = symtable

    def load_symbol_tables(self):
        source_files = self.get_source_files(self.directory)
        ast_files = self.get_ast_files(source_files)
        for source_file, ast_file in zip(source_files, ast_files):
            need_rebuild = False #判断是需要直接加载还是重新构建
            if not os.path.exists(ast_file):
                need_rebuild = True
            else:
                last_build_time = os.path.getmtime(ast_file)
                last_modified_time = os.path.getmtime(source_file)
                if last_modified_time > last_build_time:
                    need_rebuild = True
                else:
                    tu: TranslationUnit = self.parse_source_file(self.index, source_file, TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
                    for header_file in set([include.include.name for include in tu.get_includes()]):
                        last_modified_time = os.path.getmtime(header_file)
                        if last_modified_time > last_build_time:
                            #依赖的头文件更新了
                            need_rebuild = True
                            break
            if need_rebuild:
                #print(f"{source_file}: AST is obsolete or not existed")
                status, symtable = self.build_tu_symbol_table(source_file, ast_file)
                self.tu_symbol_tables[source_file] = symtable
                self.tu_status[source_file] = status
            else:
                status, symtable = self.load_tu_symbol_table(source_file, ast_file)
                self.tu_symbol_tables[source_file] = symtable    
                self.tu_status[source_file] = status
            
    def update_symbol_tables(self):
        source_files = self.get_source_files(self.directory)
        ast_files = self.get_ast_files(source_files)
        for source_file, ast_file in zip(source_files, ast_files):
            need_rebuild = False #判断是否需要重新构建
            if not os.path.exists(ast_file):
                need_rebuild = True
            else:
                last_build_time = os.path.getmtime(ast_file)
                last_modified_time = os.path.getmtime(source_file)
                if last_modified_time > last_build_time:
                    need_rebuild = True
                else:
                    tu: TranslationUnit = self.parse_source_file(self.index, source_file, TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
                    for header_file in set([include.include.name for include in tu.get_includes()]):
                        last_modified_time = os.path.getmtime(header_file)
                        if last_modified_time > last_build_time:
                            #依赖的头文件更新了
                            need_rebuild = True
                            break
            if need_rebuild:
                #print(f"{source_file}: AST is obsolete")
                status, symtable = self.build_tu_symbol_table(source_file, ast_file)
                self.tu_symbol_tables[source_file] = symtable
                self.tu_status[source_file] = status
    
    def link(self): 
        #不需要进行链接。当需要查找某个符号的依赖时，只链接该符号依赖的相关符号即可
        pass

    def find_definition_by_name(self, name, scope=None, type=None):
        #通过名字查找，结果有可能有多个
        defs = []
        if scope and not name:
            #没有指定name的情况下，scope需要是一个类的名字，返回类的定义
            target_class: Cursor = None
            for _, symbol_table in self.tu_symbol_tables.items():
                for class_node in symbol_table.classes.values():
                    full_name = CursorUtils.get_full_name(class_node)
                    if full_name[-len(scope):] == scope:
                        target_class = class_node
                        break
                if target_class:
                    break
            defs = [target_class] if target_class is not None else []
            return defs            

        ##以下这一步的效率比较低
        visited_usrs = set()
        for _, symbol_table in self.tu_symbol_tables.items():
            this_defs = symbol_table.find_definition_by_name(name=name, scope=scope, type=type)
            if len(this_defs) != 0 and scope is not None:
                return this_defs

            for this_def in this_defs:
                if this_def.get_usr() not in visited_usrs:
                    visited_usrs.add(this_def.get_usr())
                    defs.append(this_def)

        return defs        

    def find_declaration_by_name(self, name, scope=None, type=None):
        #通过名字查找，结果有可能有多个
        decls = []

        ##以下这一步的效率比较低
        visited_usrs = set()
        for _, symbol_table in self.tu_symbol_tables.items():
            this_decls = symbol_table.find_declaration_by_name(name=name, scope=scope, type=type)
            if len(this_decls) != 0 and scope is not None:
                return this_decls

            for this_decl in this_decls:
                if this_decl.get_usr() not in visited_usrs:
                    visited_usrs.add(this_decl.get_usr())    
                    decls.append(this_decl)

        return decls        

    def find_definition_by_cursor(self, cursor: Cursor, suggested_entry: str=None):
        if cursor.is_definition():
            return cursor

        #优先在建议的编译单元中查找
        entry_symbol_table = self.tu_symbol_tables.get(suggested_entry, None)
        if entry_symbol_table:
            def_cursor = entry_symbol_table.find_definition_by_cursor(cursor)
            if def_cursor:
                return def_cursor

        for _, symbol_table in self.tu_symbol_tables.items():
            if symbol_table == entry_symbol_table:
                continue
            def_cursor = symbol_table.find_definition_by_cursor(cursor)    
            if def_cursor:
                return def_cursor

        return None        

    def find_declaration_by_cursor(self, cursor: Cursor, suggested_entry: str=None):
        #优先在建议的编译单元中查找。
        entry_symbol_table = self.tu_symbol_tables.get(suggested_entry, None)
        if entry_symbol_table:
            decl_cursor = entry_symbol_table.find_declaration_by_cursor(cursor)
            if decl_cursor:
                return decl_cursor

        for _, symbol_table in self.tu_symbol_tables.items():
            if symbol_table == entry_symbol_table:
                continue
            decl_cursor = symbol_table.find_declaration_by_cursor(cursor)
            if decl_cursor:
                return decl_cursor

        return None        

    def fetch_code_snippet_from_file(self, file_name, method_defs):
        file_contents = []
        code_snippet = ""
        with open(file_name) as f:
            file_contents = f.readlines()
        lineno_width = len(str(len(file_contents)))

        line_nos = set() #记录所有需要的行号，然后从file_contents中提取对应的代码行
        for method_def in method_defs:
            if method_def.get_num_template_arguments() > 0:
                parent = method_def.semantic_parent
                for child in parent.get_children():
                    if child.location == method_def.location:
                        method_def = child
                        break
            line_nos.update([line - 1 for line in range(method_def.extent.start.line, method_def.extent.end.line+1)])
            lexical_parent = method_def.lexical_parent
            while lexical_parent and lexical_parent.kind != CursorKind.TRANSLATION_UNIT:
                if lexical_parent.kind == CursorKind.NAMESPACE:
                    children = sorted([child for child in lexical_parent.get_children()], key=lambda cursor: cursor.location.line)
                    if children:
                        first_child = children[0]
                        line_nos.update([line-1 for line in range(lexical_parent.extent.start.line, first_child.extent.start.line)])
                        line_nos.add(lexical_parent.extent.end.line-1)
                    else:
                        line_no.update([line-1 for line in range(lexical_parent.extent.start.line, lexical_parent.extent.end.line+1)])    
                lexical_parent = lexical_parent.lexical_parent    
        line_nos = sorted(line_nos)        
        line_contents = np.array(file_contents)[line_nos]
        for line_no, line_content in zip(line_nos, line_contents):
            code_snippet += str(line_no+1).rjust(lineno_width) + ": " + line_content

        return code_snippet

    def _get_call_expr_nodes(self, cursor: Cursor, filters=[], unique=False, sort=False):
        '''
        NOTE: 结果返回的是调用节点(CursorKind.CALL_EXPR)，而不是被引用节点(referenced)
        '''
        call_expr_nodes = [node for node in cursor.walk_preorder() \
            if node.kind == CursorKind.CALL_EXPR and node.referenced]
        refined_nodes = []
        for node in call_expr_nodes:
            discard = False
            for filter in filters:
                if filter(node.referenced):
                    discard = True
                    break
            if not discard:
                refined_nodes.append(node)    
        if unique:
            unique_usrs = set()
            refined_nodes = [node for node in refined_nodes if node.referenced.get_usr() \
                not in unique_usrs and not unique_usrs.add(node.referenced.get_usr())]
        if sort:        
            refined_nodes = sorted(refined_nodes, key=lambda cursor: cursor.extent.start.line)

        return refined_nodes    

    def get_call_graph(self, symbol, class_name, type=None, filters=[]):
        assert all([callable(filter) for filter in filters]), "filters must be callable!"
        method_or_func_defs = self.find_definition_by_name(name=symbol, scope=class_name, type=type)
        assert len(method_or_func_defs) == 1
        root = CallGraph(method_or_func_defs[0], None)
        queue = deque([root])
        while queue:
            callgraph = queue.popleft()
            if callgraph.has_circle:
                #如果在调用链上已经出现该节点，不再展开
                continue
            cursor = callgraph.node
            call_expr_nodes = self._get_call_expr_nodes(cursor, filters, unique=True, sort=True)
            for call_expr_node in call_expr_nodes:
                def_cursor = self.find_definition_by_cursor(call_expr_node.referenced, call_expr_node.translation_unit.spelling)
                if def_cursor is not None:
                    subgraph = CallGraph(node=def_cursor, parent=callgraph)
                    callgraph.add_subgraph(subgraph)
                    queue.append(subgraph)

        return root    

    def find_definition(self, symbol, class_name, type=None):
        method_or_func_defs = self.find_definition_by_name(name=symbol, scope=class_name, type=type)
        assert len(method_or_func_defs) != 0
        assert symbol or class_name
        if not symbol:
            key =  class_name
        elif not class_name:
            key = symbol
        else:
            key = "::".join([class_name, symbol])    
        contents = {}
        contents[key] = []

        for method_or_func_def in method_or_func_defs:
            info = {}
            info["file"] = method_or_func_def.location.file.name
            info["start_line"] = method_or_func_def.extent.start.line
            info["end_line"] = method_or_func_def.extent.end.line
            info["symbol"] = CursorUtils.get_full_name(method_or_func_def) #method_or_func_def.spelling
            info["text"] = self.get_text(method_or_func_def)
            info["is_definition"] = method_or_func_def.is_definition()
            contents[key].append(info)
        return contents    

    def find_declaration(self, symbol, class_name, type=None):
        symbol_defs = self.find_declaration_by_name(name=symbol, scope=class_name, type=type)
        if len(symbol_defs) == 0:
            symbol_defs = self.find_definition_by_name(name=symbol, scope=class_name, type=type)

        assert len(symbol_defs) != 0
        assert symbol or class_name
        if not symbol:
            key =  class_name
        elif not class_name:
            key = symbol
        else:
            key = "::".join([class_name, symbol])    
        contents = {}
        contents[key] = []

        for symbol_decl in symbol_defs:
            info = {}
            info["file"] = symbol_decl.location.file.name
            info["start_line"] = symbol_decl.extent.start.line
            info["end_line"] = symbol_decl.extent.end.line
            info["symbol"] = CursorUtils.get_full_name(symbol_decl)#symbol_decl.spelling
            info["text"] = self.get_text(symbol_decl)
            info["is_definition"] = symbol_decl.is_definition()
            contents[key].append(info)

        return contents    

    def get_text(self, cursor:Cursor):
        #TODO: 模板实例化可能丢掉前面的template<XXXX>
        if cursor.get_num_template_arguments() != -1:
            parent = cursor.semantic_parent
            for child in parent.get_children():
                if child.location == cursor.location:
                    cursor = child
                    break
        file = cursor.location.file.name
        start, end = cursor.extent.start.line, cursor.extent.end.line
        with open(file) as filp:
            contents = filp.readlines()
        text = ''.join(contents[start-1:end])       
        return text
        
    def fetch_method_context(self, symbol, scope, type=None, filters=[]):
        method_defs = self.find_definition_by_name(name=symbol, scope=scope, type=type)
        if len(method_defs) == 0:
            symbol = '::'.join([scope, symbol]) if scope else symbol
            return f"Can't find the specified symbol {symbol}, please check the symbol name or scope name, then try again"
        all_context = [method_def for method_def in method_defs]    
        visited_usrs = set([method_def.get_usr() for method_def in method_defs])
        for method_def in method_defs:
            semantic_parent = method_def.semantic_parent
            if CursorUtils.is_class_definition(semantic_parent) and semantic_parent.get_usr() not in visited_usrs:
                visited_usrs.add(semantic_parent.get_usr())
                all_context.append(semantic_parent)

        for method_def in method_defs:
            call_expr_nodes = self._get_call_expr_nodes(method_def, filters, True, False)
            for call_expr_node in call_expr_nodes:
                referenced = call_expr_node.referenced
                semantic_parent = referenced.semantic_parent
                if CursorUtils.is_class_definition(semantic_parent) and semantic_parent.get_usr() not in visited_usrs:
                    visited_usrs.add(semantic_parent.get_usr())
                    all_context.append(semantic_parent)

        code_snippets = {}
        code_methods = {}
        for method_def in all_context:
            file_name = method_def.location.file.name
            if file_name in code_methods.keys():
                code_methods[file_name].append(method_def)
            else:
                code_methods[file_name] = [method_def]

        for file_name, method_defs in code_methods.items():
            sorted_method_defs = sorted(method_defs, key=lambda method_def: method_def.extent.start.line)
            code_snippets[file_name] = self.fetch_code_snippet_from_file(file_name, sorted_method_defs)  

        return self.format_code_snippets(code_snippets)    
        
    def fetch_source_code_v2(self, symbol, scope, type=None):
        #提取scope::method_or_func有关的代码
        method_deps = self.find_definition_by_name(name=symbol, scope=scope, type=type)
        if len(method_deps) == 0:
            symbol = '::'.join([scope, symbol]) if scope else symbol
            return f"Can't find the specified symbol {symbol}, please check the symbol name or scope name, then try again"
        code_snippets = {}
        code_methods = {}

        if method_deps:
            #对method_refs按照文件名归类，确定文件的哪些行被引用到
            for method_def in method_deps:
                file_name = method_def.location.file.name
                if file_name in code_methods.keys():
                    code_methods[file_name].append(method_def)
                else:
                    code_methods[file_name] = [method_def]

                class_def = method_def.semantic_parent
                if CursorUtils.is_class_definition(class_def):
                    #如果是方法，把方法的类定义也加进来
                    file_name = class_def.location.file.name
                    if file_name in code_methods.keys():
                        #TODO: 避免重复加入
                        code_methods[file_name].append(class_def)
                    else:
                        code_methods[file_name] = [class_def]

            for file_name, method_defs in code_methods.items():
                sorted_method_defs = sorted(method_defs, key=lambda method_def: method_def.extent.start.line)
                code_snippets[file_name] = self.fetch_code_snippet_from_file(file_name, sorted_method_defs)  

        return self.format_code_snippets(code_snippets)
        
    def fetch_source_code(self, symbol, scope, type=None, filters=[], with_header=True):
        #提取scope::method_or_func有关的代码
        assert all([callable(filter) for filter in filters]), "filters must be callable!"
        method_or_func_def = self.find_definition_by_name(name=symbol, scope=scope, type=type)
        if len(method_or_func_def) == 0:
            symbol = '::'.join([scope, symbol]) if scope else symbol
            return f"Can't find the specified symbol {symbol}, please check the symbol name or scope name, then try again"
        method_deps = []
        code_snippets = {}
        code_methods = {}
        if method_or_func_def:
            method_deps = self.find_dependence(method_or_func_def, filters)

        if method_deps:
            #对method_refs按照文件名归类，确定文件的哪些行被引用到
            for method_def in method_deps:
                file_name = method_def.location.file.name
                if file_name in code_methods.keys():
                    code_methods[file_name].append(method_def)
                else:
                    code_methods[file_name] = [method_def]

                if with_header:
                    class_def = method_def.semantic_parent
                    if CursorUtils.is_class_definition(class_def):
                        #如果是方法，把方法的类定义也加进来
                        file_name = class_def.location.file.name
                        if file_name in code_methods.keys():
                            #TODO: 避免重复加入
                            code_methods[file_name].append(class_def)
                        else:
                            code_methods[file_name] = [class_def]

            for file_name, method_defs in code_methods.items():
                sorted_method_defs = sorted(method_defs, key=lambda method_def: method_def.extent.start.line)
                code_snippets[file_name] = self.fetch_code_snippet_from_file(file_name, sorted_method_defs)  

        return self.format_code_snippets(code_snippets)

    def format_code_snippets(self, code_snippets):
        code = ""
        for file_name, code_snippet in code_snippets.items():
            if file_name.endswith((".h", ".hpp", ".cuh")):
                code += "```cpp\n"
                code += f"//file_name: {file_name}\n"
                code += code_snippet
                code += "```\n\n" if code.endswith("\n") else "\n```\n\n"
        for file_name, code_snippet in code_snippets.items():
            if not file_name.endswith((".h", ".hpp", ".cuh")):
                code += "```cpp\n"
                code += f"//file_name: {file_name}\n"
                code += code_snippet
                code += "```\n\n" if code.endswith("\n") else "\n```\n\n"

        return code

    def find_dependence(self, method_defs, filters=[]):
        if isinstance(method_defs, Cursor):
            method_defs = [method_defs]
        task_queue = deque([method_def for method_def in method_defs])
        visited_usrs = set([method_def.get_usr() for method_def in method_defs])

        all_deps: List[Cursor] = [] #记录method_defs依赖的方法/函数
        while task_queue:
            method_def = task_queue.popleft()
            all_deps.append(method_def)
            call_expr_nodes = self._get_call_expr_nodes(method_def, filters, unique=False, sort=False)
            for call_expr_node in call_expr_nodes:
                referenced = call_expr_node.referenced
                if CursorUtils.is_callable(referenced) and referenced.get_usr() not in visited_usrs:
                    method_def = referenced if referenced.is_definition() else \
                        self.find_definition_by_cursor(referenced, call_expr_node.translation_unit.spelling)
                    if method_def:
                        task_queue.append(method_def)
                        visited_usrs.add(referenced.get_usr())    

        return all_deps

if __name__ == "__main__":
    from transformers import AutoTokenizer
    #src = '/home/wnk/code/GalSim/tmp/no_tpl'  # Change this to the path of your source code directory
    #include = ['/home/wnk/code/GalSim/tmp/no_tpl']  # Change this to the path of your include directory
    #test_clang_includes()

    configs = [ 
        {
            "src": "/home/wnk/code/GalSim/src",
            "include": ["/home/wnk/code/GalSim/include", "/home/wnk/code/GalSim/include/galsim", "/home/wnk/code/GalSim/src",  "/home/wnk/code/GalSim/src/cuda_kernels", "/home/wnk/code/GalSim/downloaded_eigen/eigen-3.4.0"],
            #"scope": "galsim::SBSpergel::SBSpergelImpl",
            "scope": "SBConvolveImpl",
            "method": "shoot",
            "namespaces": [],
            "cache_dir": "/home/jiangbo/agentflow/cached_ast_dir/galsim",
            "use_cache": False,
            "output_filters": [
                lambda cursor: not cursor.location.file.name.startswith("/home/jiangbo/GalSim"),
                #lambda cursor: not CursorUtils.get_namespace(cursor) == "galsim"
            ]
        }
        ,{
            "src": "/home/jiangbo/arctic/arctic/src",
            "include": ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"],

            "scope": "",
            "method": "add_cti",

            #"scope": "",
            #"method": "clock_charge_in_one_direction",

            #"scope": "TrapManagerInstantCapture",
            #"method": "n_electrons_released",

            "namespaces": [],
            "cache_dir": "/home/jiangbo/AutoCoder/cached_ast_dir/arctic",
            "use_cache": False,
            "output_filters": [
                lambda cursor: not cursor.location.file.name.startswith("/home/jiangbo/arctic/arctic")
            ]
        }
    ]

    config = configs[0]

    src = config["src"]
    include = config["include"]
    namespaces = config["namespaces"]
    cache_dir = config["cache_dir"]
    use_cache = config["use_cache"]
    output_filters = config["output_filters"]
    method = config["method"]
    scope = config["scope"]

    ast = AST()
    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_dir, load=use_cache)

    tokenizer = AutoTokenizer.from_pretrained("/home/jiangbo/models")
    scope_methods = [
        "galsim::PhotonArray::setFrom",
        "galsim::PhotonArray::getTotalFlux",
        "galsim::PhotonArray::scaleXY",
        "galsim::PhotonArray::scaleFlux",
        "galsim::PhotonArray::assignAt",
        "galsim::PhotonArray::convolve",
        "galsim::PhotonArray::convolveShuffle",
        "galsim::PhotonArray::addTo",

        "galsim::Nearest::shoot",
        "galsim::Delta::shoot",
        "galsim::Linear::shoot",
        "galsim::SBBox::SBBoxImpl::shoot",
        "galsim::SBTopHat::SBTopHatImpl::shoot",
        "galsim::SBDeltaFunction::SBDeltaFunctionImpl::shoot",
        "galsim::SBGaussian::SBGaussianImpl::shoot",
        "galsim::SBMoffat::SBMoffatImpl::shoot",
        "galsim::SBTransform::SBTransformImpl::shoot",

        "galsim::SBAiry::SBAiryImpl::shoot",
        "galsim::SBExponential::SBExponentialImpl::shoot",
        "galsim::SBKolmogorov::SBKolmogorovImpl::shoot",
        "galsim::SBSpergel::SBSpergelImpl::shoot",
        "galsim::SBSersic::SBSersicImpl::shoot",
        "galsim::SBSecondKick::SBSecondKickImpl::shoot",
        "galsim::SBVonKarman::SBVonKarmanImpl::shoot",
        "galsim::SBInterpolatedImage::SBInterpolatedImageImpl::shoot",

        "galsim::OneDimensionalDeviate::shoot",

        "galsim::SBAutoConvolve::SBAutoConvolveImpl::shoot",
        "galsim::SBAutoCorrelate::SBAutoCorrelateImpl::shoot",
        "galsim::SBConvolve::SBConvolveImpl::shoot",
        "galsim::SBAdd::SBAddImpl::shoot",
    ]

    for scope_method in scope_methods:
        scope_method = scope_method.split("::")
        scope = "::".join(scope_method[:-1])
        method = scope_method[-1]

        code_snippets = ast.fetch_source_code(method, scope, type=None, filters=output_filters, with_header=True)
        tokens = tokenizer.encode(code_snippets)
        print(f"{'::'.join(scope_method)} {len(code_snippets.splitlines())} {len(tokens)}")


    #callgraph = ast.get_call_graph(method, scope, filters=output_filters)
    #print(callgraph.to_string(remove_leaf_nodes=False))
    #callgraph.draw_callgraph()
    #code_snippets = ast.fetch_source_code(method, scope, type=None, filters=output_filters)
    #print(code_snippets)
    print(ast.find_definition(method, class_name=scope))
    print(json.dumps(ast.find_declaration(method, class_name=scope)))




