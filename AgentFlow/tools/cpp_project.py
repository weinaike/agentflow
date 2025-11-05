from hashlib import md5
import json
import os
import time
from clang.cindex import Index, Cursor, CursorKind, TypeKind
import numpy as np
from typing import List, Union
from collections import deque
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .project_base import ProjectBase
from parser_base import ParserBase
from clang_parser import ClangParser, ParsedTu, TypeUtils, CursorUtils, CallGraph

from .memgraph.graph_service import MemgraphIngestor

class CppProject(ProjectBase):
    def __init__(self, 
                 build_options: List[str]=[], 
                 force_build: bool = False,
                 build_dir: str = None,
                 root_dir: str = None,
                 src_dirs: List[str]=[], 
                 filter_by_dirs: List[str]=[], filter_by_namespaces: List[str]=[]
    ):
        self.build_options = build_options
        self.force_build = force_build
        self.build_dir = build_dir
        self.root_dir = root_dir
        self.src_dirs = src_dirs
        self.filter_by_dirs = filter_by_dirs
        self.filter_by_namespaces = filter_by_namespaces
        self.filters = []
        # if self.filter_by_dirs:
        #     self.filters.append(lambda cursor: not any([os.path.commonpath([dir, cursor.location.file.name]) == dir for dir in self.filter_by_dirs]))
        # if self.filter_by_namespaces:
        #     self.filters.append(lambda cursor: CursorUtils.get_namespace(cursor) not in self.filter_by_namespaces)

        self.scope_checkers = []
        self.filter_by_dirs = filter_by_dirs or []
        self.scope_checkers.append(
            lambda cursor: any([cursor.location.file is not None and 
                                os.path.commonpath([dir, cursor.location.file.name]) == dir for dir in self.filter_by_dirs])
        )
        self.namespace_scopes = filter_by_namespaces or []
        # self.scope_checkers.append(
        #     lambda cursor: CursorUtils.get_namespace(cursor) in self.namespace_scopes
        # )
                
        self.index = Index.create()
        self.parser: ParserBase = ClangParser(scope_checkers=self.scope_checkers)

        self.parsed_tus = {}

        self.parse()

    def __hash__(self) -> str:
        if hasattr(self, "md5_hash"):
            return self.md5_hash
        else:
            import hashlib    
            args = []
            args.extend(sorted(list(map(str, self.build_options))))
            #args.append(str(self.force_build))
            #args.append(str(self.build_dir))
            args.extend(sorted(list(map(str, self.src_dirs))))
            args.extend(sorted(list(map(str, self.filter_by_dirs))))
            args.extend(sorted(list(map(str, self.filter_by_namespaces))))
            key = "::".join(args).encode("utf-8")
            hash_obj = hashlib.sha256(key)
            self.md5_hash = "cpp_" + hash_obj.hexdigest()[:16]
            return self.md5_hash

    def get_makefile(self):
        if self.root_dir:
            files = os.listdir(self.root_dir)
            makefile_name = None
            for filename in files:
                if filename.upper() == 'MAKEFILE':
                    makefile_name = os.path.join(self.root_dir, filename)
                    break
            if makefile_name:
                with open(makefile_name) as f:
                    content = f.read()   
                return f"```makefile\n# filename: {makefile_name}\n{content}\n```\n"    
                
        return "Makefile doesn't exist in the project.\n"        
            
    def need_parse(self, source_file):
        if self.force_build:
            return True

        last_modified_time = os.path.getmtime(source_file)    
        parsed_tu: ParsedTu = self.parsed_tus.get(source_file, None)    
        if parsed_tu: # has been loaded into memory
            if parsed_tu.parse_time < last_modified_time:
                return True
            include_header_files = self.parser.get_include_headers(source_file, self.index, self.build_options)    
            for include_header_file in include_header_files:
                if os.path.getmtime(include_header_file) > last_modified_time:
                    return True
        else:
            # check the cached ast file
            if self.build_dir is None:
                return True
            ast_file = self._generate_ast_file_name(source_file)
            if os.path.exists(ast_file):
                parsed_time = os.path.getmtime(ast_file) # TODO: Refine me
                if last_modified_time > parsed_time:
                    return True

                include_header_files = self.parser.get_include_headers(source_file, self.index, self.build_options)    
                for include_header_file in include_header_files:
                    if os.path.getmtime(include_header_file) > last_modified_time:
                        return True
                # the cache file
                self.parsed_tus[source_file] = self.parser.parse(ast_file)
                return False
            elif not os.path.exists(ast_file):
                return True

        return False        
    
    def list_source_files(self) -> List[str]:
        source_files = []
        for directory in self.src_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(('.cpp', '.c', '.cu', '.cc', '.cxx')):
                        source_files.append(os.path.abspath(os.path.join(root, file)))
        return source_files

    def _generate_ast_file_name(self, source_file: str):
        target_dir,  target_dirname_len = "", 4096
        src_filename_len = len(source_file)
        for dir in self.src_dirs:
            dir_len = len(dir)
            if dir_len <= src_filename_len and source_file[:dir_len] == dir:
                if dir_len < target_dirname_len:
                    target_dir = dir
                    target_dirname_len = dir_len
        relpath = source_file[target_dirname_len+1:]
        return os.path.join(self.build_dir, relpath + ".ast")

    def parse(self):
        if self.build_dir is not None:
            hash_file = os.path.join(self.build_dir, ".__hash__")
            if os.path.exists(hash_file):
                with open(hash_file, "r") as f:
                    old_hash = f.read()
                if self.__hash__() != old_hash:
                    import shutil
                    shutil.rmtree(self.build_dir)    
            os.makedirs(self.build_dir, exist_ok=True)
            with open(hash_file, "w") as f:
                f.write(self.__hash__())        

        prev_source_files = set(self.parsed_tus.keys())
        curr_source_files = set(self.list_source_files())
        for source_file in  prev_source_files - curr_source_files:
            del self.parsed_tus[source_file]

        for source_file in curr_source_files:
            ast_file = self._generate_ast_file_name(source_file)
            if self.need_parse(source_file):
                parsed_tu: ParsedTu = self.parser.parse(filename=source_file, index=self.index, args=self.build_options)
                self.parsed_tus[source_file] = parsed_tu
                if self.build_dir:
                    os.makedirs(os.path.dirname(ast_file), exist_ok=True)
                    parsed_tu.tu.save(ast_file)

    def find_definition_by_name(self, symbol, type=None):
        defs = []
        visited_usrs = set()
        for _, parsed_tu in self.parsed_tus.items():
            this_defs = parsed_tu.find_class_by_name(symbol, type=type)
            if len(this_defs) != 0:
                return this_defs

        for _, symbol_table in self.parsed_tus.items():
            this_defs = symbol_table.find_definition_by_name(symbol, type=type)

            for this_def in this_defs:
                if this_def.get_usr() not in visited_usrs:
                    visited_usrs.add(this_def.get_usr())
                    defs.append(this_def)

        return defs        

    def find_definition_by_usr(self, usr: str):
        for _, parsed_tu in self.parsed_tus.items():
            def_cursor = parsed_tu.find_definition_by_usr(usr)
            if def_cursor:
                return def_cursor
        return None
        
    def find_definition_by_cursor(self, cursor: Cursor, suggested_entry: str=None):
        if cursor.is_definition():
            return cursor

        #优先在建议的编译单元中查找
        suggested_parsed_tu = self.parsed_tus.get(suggested_entry, None)
        if suggested_parsed_tu:
            def_cursor = suggested_parsed_tu.find_definition_by_cursor(cursor)
            if def_cursor:
                return def_cursor

        for _, parsed_tu in self.parsed_tus.items():
            if parsed_tu == suggested_parsed_tu:
                continue
            def_cursor = parsed_tu.find_definition_by_cursor(cursor)    
            if def_cursor:
                return def_cursor

        return None        

    def find_declaration_by_name(self, symbol, type=None):
        defs = []
        visited_usrs = set()

        for _, symbol_table in self.parsed_tus.items():
            this_defs = symbol_table.find_declaration_by_name(symbol, type=type)

            for this_def in this_defs:
                if this_def.get_usr() not in visited_usrs:
                    visited_usrs.add(this_def.get_usr())
                    defs.append(this_def)

        return defs        

    def find_declaration_by_usr(self, usr: str):
        for _, ptu in self.parsed_tus.items():
            decl_cursor = ptu.find_declaration_by_usr(usr)
            if decl_cursor:
                return decl_cursor
            
        return None
        
    def find_declaration_by_cursor(self, cursor: Cursor, suggested_entry: str=None):
        entry: ParsedTu = self.parsed_tus.get(suggested_entry, None)
        if entry:
            decl_cursor = entry.find_declaration_by_cursor(cursor)
            if decl_cursor:
                return decl_cursor

        for _, parsed_tu in self.parsed_tus.items():
            if parsed_tu == entry:
                continue
            decl_cursor = parsed_tu.find_declaration_by_cursor(cursor)
            if decl_cursor:
                return decl_cursor

        return None        

    def get_call_expr_nodes(self, cursor: Cursor, filters=[], unique=False, sort=False):
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

    def get_for_stmts(self, cursor: Cursor) ->List[Cursor]:    
        for_stmts = [node for node in cursor.walk_preorder() \
                if node.kind == CursorKind.FOR_STMT
            ]
        return for_stmts    

    def get_all_subclasses(self, cursor: Cursor):
        subclasses = []
        for ptu in self.parsed_tus.values():
            for clazz in ptu.classes.values():    
                if CursorUtils.is_ancestor_of(cursor, clazz):
                    subclasses.append(clazz)
        return subclasses            

    def get_overridden_methods(self, cursor: Cursor):
        overridden_methods = []
        if not cursor.is_virtual_method():
            return overridden_methods

        class_node = cursor.semantic_parent   
        subclasses = self.get_all_subclasses(class_node)
        for subclass in subclasses:
            methods = CursorUtils.get_class_methods(subclass)
            for method in methods:
                if method.is_virtual_method() and method.spelling == cursor.spelling and \
                    method.type.spelling == cursor.type.spelling:
                    overridden_methods.append(method)        
        return overridden_methods            


    def _get_data_types_recursively(self, cursor: Cursor, broadcast=False):
        def __get_data_types(cursor: Cursor):
            data_types = [node.type for node in cursor.walk_preorder() \
                if node.kind in [CursorKind.VAR_DECL, CursorKind.PARM_DECL, CursorKind.FIELD_DECL]]   
            data_types = [TypeUtils.get_ultimate_type(dt) for dt in data_types]    
            data_types = { dt.get_declaration().get_usr(): dt for dt in data_types if dt.get_declaration().get_usr() != ''}
            return list(data_types.values())

        visited_types = set()
        data_types = __get_data_types(cursor)
        if not broadcast:
            return data_types
        
        visited_types.update([dt.get_declaration().get_usr() for dt in data_types])
        queue = deque([dt.get_declaration() for dt in data_types])
        while queue:
            cursor = queue.popleft()
            dts = __get_data_types(cursor)
            unvisited_data_types = [dt for dt in dts if dt.get_declaration().get_usr() not in visited_types]
            data_types.extend(unvisited_data_types)
            visited_types.update([dt.get_declaration().get_usr() for dt in unvisited_data_types])
            queue.extend([dt.get_declaration() for dt in unvisited_data_types])

        return data_types    

    def find_dependence(self, method_defs, filters=[]):
        if isinstance(method_defs, Cursor):
            method_defs = [method_defs]
        task_queue = deque([method_def for method_def in method_defs])
        visited_usrs = set([method_def.get_usr() for method_def in method_defs])

        all_deps: List[Cursor] = [] #记录method_defs依赖的方法/函数
        while task_queue:
            method_def = task_queue.popleft()
            all_deps.append(method_def)
            call_expr_nodes = self.get_call_expr_nodes(method_def, filters, unique=False, sort=False)
            for call_expr_node in call_expr_nodes:
                referenced = call_expr_node.referenced
                if CursorUtils.is_callable(referenced) and referenced.get_usr() not in visited_usrs:
                    method_def = referenced if referenced.is_definition() else \
                        self.find_definition_by_cursor(referenced, call_expr_node.translation_unit.spelling)
                    if method_def:
                        task_queue.append(method_def)
                        visited_usrs.add(referenced.get_usr())    

        return all_deps

    def inspect(self, *, symbol=None, usr=None, cursor=None, type=None):
        symbol_defs, symbol_decls = [], []
        if symbol:
            symbol_defs.extend(self.find_definition_by_name(symbol=symbol, type=type))
            symbol_decls.extend(self.find_declaration_by_name(symbol=symbol, type=type))
        elif usr:
            symbol_def = self.find_definition_by_usr(usr)
            symbol_decl = self.find_declaration_by_usr(usr)

            symbol_defs = [symbol_def] if symbol_def else []
            symbol_decls = [symbol_decl] if symbol_decl else []
        elif cursor:    
            symbol_def = self.find_definition_by_usr(usr)
            symbol_decl = self.find_declaration_by_usr(usr)

            symbol_defs = [symbol_def] if symbol_def else []
            symbol_decls = [symbol_decl] if symbol_decl else []
            
        if len(symbol_defs) == 0:
            return {"success": False, "reason": {f"the specified symbol {symbol} with type {type or 'None'} not found in the project"}}
        assert len(symbol_defs) == 1, f"{symbol}: find {len(symbol_defs)} symbols: "
        def_cursor: Cursor = symbol_defs[0]
        callees = self.get_call_expr_nodes(def_cursor, filters=[], unique=True, sort=True)    
        data_types = self._get_data_types_recursively(def_cursor, broadcast=True)
        type_defs = [dt.get_declaration() for dt in data_types]

        callees_in_project = [callee.referenced for callee in callees if not CursorUtils.is_out_of_any_scope(callee.referenced, self.scope_checkers)]
        callees_out_of_project = [callee.referenced for callee in callees if CursorUtils.is_out_of_any_scope(callee.referenced, self.scope_checkers)]

        type_defs_in_project = [type_def for type_def in type_defs if not CursorUtils.is_out_of_any_scope(type_def, self.scope_checkers)]
        type_defs_out_of_project = [type_def for type_def in type_defs if CursorUtils.is_out_of_any_scope(type_def, self.scope_checkers)]
        return {
            "callees": callees,
            "callees_in_project": callees_in_project,
            "callees_out_of_project": callees_out_of_project,
            "type_defs": type_defs,
            "type_defs_in_project": type_defs_in_project,
            "type_defs_out_of_project": type_defs_out_of_project,
            "definition": def_cursor,
            "declaration": symbol_decls[0] if symbol_decls else None
        }
            
    def find_definition(self, symbol, type=None, requires_lines=True):    
        method_or_func_defs = self.find_definition_by_name(symbol=symbol, type=type)

        key = symbol
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

    def find_declaration(self, symbol, type=None):
        symbol_defs = self.find_declaration_by_name(symbol=symbol, type=type)
        if len(symbol_defs) == 0:
            symbol_defs = self.find_definition_by_name(symbol=symbol, type=type)

        key = symbol
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

    def get_text(self, cursor):
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

    def get_call_graph(self, symbol, type=None):
        method_or_func_defs = self.find_definition_by_name(symbol, type)
        assert len(method_or_func_defs) == 1
        root = CallGraph(method_or_func_defs[0], None)
        queue = deque([root])
        while queue:
            callgraph = queue.popleft()
            if callgraph.has_circle:
                #如果在调用链上已经出现该节点，不再展开
                continue
            cursor = callgraph.node
            call_expr_nodes = CursorUtils.get_callees(cursor, unique=True)
            for call_expr_node in call_expr_nodes:
                def_cursor = self.find_definition_by_cursor(call_expr_node.referenced, call_expr_node.translation_unit.spelling)
                if def_cursor is not None:
                    subgraph = CallGraph(node=def_cursor, parent=callgraph)
                    callgraph.add_subgraph(subgraph)
                    queue.append(subgraph)

        return root    

    def draw_complete_graph(self, filename):
        class GraphNode:
            def __init__(self, node: Cursor, fillcolor):
                self.node_id = md5(node.get_usr().encode()).hexdigest()[:8]
                self.node_label = CursorUtils.get_full_name(node)
                #self.node_label = CursorUtils.get_full_displayname(node)
                self.fillcolor = fillcolor

            def __hash__(self):
                return int(self.node_id, base=16)    

            def __eq__(self, other):
                return self.node_id == other.node_id    
        class GraphEdge:
            def __init__(self, src, dst, color):
                self.src_id = md5(src.get_usr().encode()).hexdigest()[:8]
                self.dst_id = md5(dst.get_usr().encode()).hexdigest()[:8]
                self.color = color        

            def __hash__(self):
                return (int(self.src_id, base=16) << 8) + int(self.dst_id, base=16)   

            def __eq__(self, other):
                return self.src_id == other.src_id and self.dst_id == other.dst_id    

        graph_nodes, graph_edges = set(), set()
        
        for ptu in self.parsed_tus.values():
            for def_cursor in ptu.def_cursors.values():
                if not CursorUtils.is_callable(def_cursor):
                    continue
                if CursorUtils.is_out_of_any_scope(def_cursor, self.scope_checkers):
                    continue
                    
                all_callees = CursorUtils.get_callees(def_cursor, unique=True)
                for_stmts = CursorUtils.get_for_stmts(def_cursor)
                callees_in_loop = set()
                for for_stmt in for_stmts:
                    callees_in_loop.update([callee.referenced.get_usr() for callee in CursorUtils.get_callees(for_stmt)])

                callees = [callee for callee in all_callees if not callee.referenced.is_default_method()]    

                for callee in callees:
                    referenced = callee.referenced
                    out_of_scope = CursorUtils.is_out_of_any_scope(referenced, self.scope_checkers)
                    if out_of_scope:
                        continue

                    if def_cursor.get_usr() == referenced.get_usr():
                        # to avoid self-loop
                        continue
                    color = "red" if referenced.get_usr() in callees_in_loop else "blue"
                    graph_edges.add(GraphEdge(def_cursor, referenced, color))
                    if out_of_scope:
                        fillcolor = "gray" if out_of_scope else "lightblue"
                        graph_nodes.add(GraphNode(referenced, fillcolor))

                # The node is in scope
                node = GraphNode(def_cursor, "red" if len(for_stmts) != 0 else "lightblue")        
                graph_nodes.add(node)
                overridden_method = CursorUtils.get_overridden_method(def_cursor)
                if overridden_method:
                    # edge = GraphEdge(overridden_method, def_cursor, "purple")
                    # graph_edges.add(edge)
                    pass

            # for decl_cursor in ptu.decl_cursors.values():        
            #     if not CursorUtils.is_callable(decl_cursor):
            #         continue
            #     if CursorUtils.is_out_of_any_scope(decl_cursor, self.scope_checkers):
            #         continue
            #     node = GraphNode(decl_cursor, "lightblue")        
            #     graph_nodes.add(node)

        print(f"nodes: {len(graph_nodes)}; edges: {len(graph_edges)}")
        from graphviz import Digraph
        dot = Digraph(comment="call graph")
        dot.attr(rankdir="LR")
        dot.attr("node", shape="box", style='filled', fillcolor='lightblue')
        for node in graph_nodes:
            dot.node(node.node_id, node.node_label, fillcolor=node.fillcolor)
        for edge in graph_edges:
            dot.edge(edge.src_id, edge.dst_id, color=edge.color)    

        try:
            dot.format = "png"
            dot.render(filename, view=False, cleanup=True)  
            dot.format = "svg"
            dot.render(filename, view=False, cleanup=True)  
        except Exception as e:
            print(e)    

    def fetch_context(self,*, symbol=None, usr=None, cursor=None, type=None):
        assert sum(1 for param in [symbol, usr, cursor] if param is not None) == 1, \
            "Exactly one of the parameters (symbol, usr, cursor) must be provided."
        
        results = self.inspect(symbol=symbol, usr=usr, cursor=cursor, type=type)
        callees, callees_in_project, callees_out_of_project, type_defs, type_defs_in_project, type_defs_out_of_project, symbol_def, symbol_decl = (
            results[key] for key in ("callees", "callees_in_project", "callees_out_of_project", "type_defs", "type_defs_in_project", "type_defs_out_of_project", "definition", "declaration")
        )
        symbol = CursorUtils.get_full_name(symbol_def)
        context = "### Context Before Translation\n"
        if callees_in_project:
            context += f"{symbol} calls the following function(s) which are implemented in current project: \n"
            for callee in callees_in_project:
                context += f"  -  {CursorUtils.get_full_name(callee)}\n"
        if callees_out_of_project:
            context += f"{symbol} calls the following third-party library function(s): \n"
            for callee in callees_out_of_project:
                context += f"  -  {CursorUtils.get_full_name(callee)}\n"
                    
        if type_defs_in_project:
            context += f"{symbol} depends on the following data structure(s) which are defined in current project: \n"
            for type_def in type_defs_in_project:
                context += f"  -  {CursorUtils.get_full_displayname(type_def)}\n"
        if type_defs_out_of_project:
            context += f"{symbol} depends on the following third-party library data structures: \n"
            for type_def in type_defs_out_of_project:
                context += f"  -  {CursorUtils.get_full_displayname(type_def)}\n"
                    
        if symbol_decl:
            context += f"{symbol} is declared in the file {symbol_decl.location.file.name}.\n\n"

        code_snippets = {}
        code_methods = {}
        method_deps = [symbol_def, symbol_decl] if symbol_decl else [symbol_def]  
        method_deps.extend(callees_in_project)
        method_deps.extend(type_defs_in_project)

        for method_def in method_deps:
            file_name = method_def.location.file.name
            if file_name in code_methods.keys():
                code_methods[file_name].append(method_def)
            else:
                code_methods[file_name] = [method_def]

        for file_name, method_defs in code_methods.items():
            sorted_method_defs = sorted(method_defs, key=lambda method_def: method_def.extent.start.line)
            code_snippets[file_name] = self.fetch_code_snippet_from_file(file_name, sorted_method_defs, requires_complete_code=False, requires_line_nos=False)  
        code_snippets = self.format_code_snippets(code_snippets)    

        context += f"The code related to {symbol} is listed as follows: \n\n "
        context += code_snippets

        return context

    
    def fetch_source_code(self, symbol, type=None, requires_lines=True, requires_classes=True, requires_complete_target_files: Union[None, List[str]]=[]):
        method_or_func_def = self.find_definition_by_name(symbol, type=type)
        if len(method_or_func_def) == 0:
            return f"Can't find the specified symbol `{symbol}'"
        method_deps = []
        code_snippets = {}
        code_methods = {}
        target_file_names = set([method_def.location.file.name for method_def in method_or_func_def])
        if method_or_func_def:
            method_deps = self.find_dependence(method_or_func_def, self.scope_checkers)

        if method_deps:
            #对method_refs按照文件名归类，确定文件的哪些行被引用到
            for method_def in method_deps:
                file_name = method_def.location.file.name
                if file_name in code_methods.keys():
                    code_methods[file_name].append(method_def)
                else:
                    code_methods[file_name] = [method_def]

                if requires_classes:
                    class_def = method_def.semantic_parent
                    if CursorUtils.is_class_definition(class_def):
                        #如果是方法，把方法的类定义也加进来
                        file_name = class_def.location.file.name
                        if file_name in code_methods.keys():
                            #TODO: 避免重复加入
                            code_methods[file_name].append(class_def)
                        else:
                            code_methods[file_name] = [class_def]
                    infos = self.inspect(method_def)        
                    type_defs = infos.get("type_defs_in_project", [])
                    for type_def in type_defs:
                        file_name = type_def.location.file.name
                        if file_name in code_methods.keys():
                            code_methods[file_name].append(type_def)
                        else:
                            code_methods[file_name] = [type_def]    

            for file_name, method_defs in code_methods.items():
                sorted_method_defs = sorted(method_defs, key=lambda method_def: method_def.extent.start.line)
                code_snippets[file_name] = self.fetch_code_snippet_from_file(file_name, sorted_method_defs, requires_complete_code=requires_complete_target_files and file_name in target_file_names, requires_line_nos=True)  

        return self.format_code_snippets(code_snippets)

    def fetch_code_snippet_from_file(self, file_name, method_defs, *, requires_complete_code=False, requires_line_nos=True):
        file_contents = []
        code_snippet = ""
        OMITTED_CODE = "        // ... lines {start}-{end} omitted for brevity\n"
        #print(f"reading file {file_name}", file=sys.stderr)
        with open(file_name, errors='ignore') as f:
            file_contents = f.readlines()
        lineno_width = len(str(len(file_contents)))

        line_nos = set() #记录所有需要的行号，然后从file_contents中提取对应的代码行
        if requires_complete_code:
            line_nos = np.arange(len(file_contents)).tolist()
        else:    
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

        prev_line = -1
        line_no_width = len(str(np.max(line_nos)))
        line_no_width = (line_no_width + 3) // 4 * 4
        for line_no in line_nos:
            if line_no > prev_line + 1:
                start, end = prev_line + 1, line_no - 1
                if start == end and not file_contents[start].strip():
                    if requires_line_nos:
                        code_snippet += f"{start+1:>{line_no_width}}:   {file_contents[start]}"
                    else:
                        code_snippet += file_contents[start]    
                else:    
                    if requires_line_nos:
                        code_snippet += OMITTED_CODE.format(start=start+1, end=end+1)    
            if requires_line_nos:
                code_snippet += f"{line_no+1:>{line_no_width}}:   {file_contents[line_no]}"
            else:
                code_snippet += file_contents[line_no]    
            prev_line = line_no

        if prev_line < len(file_contents) -1:
            start, end = prev_line + 1, len(file_contents) - 1
            if start == end and not file_contents[start].strip():
                if requires_line_nos:
                    code_snippet += f"{start+1:>{line_no_width}}:   {file_contents[start]}"
                else:
                    code_snippet += file_contents[start]    
            else:    
                if requires_line_nos:
                    code_snippet += OMITTED_CODE.format(start=start+1, end=end+1)  

        return code_snippet

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

def TEST_galsim_project():
    
    config = {
        "build_options": ["-I/home/jiangbo/GalSim/include", "-I/home/jiangbo/GalSim/include/galsim", "-std=c++14", "-DENABLE_CUDA", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include"], 
        "force_build": True,
        "build_dir": "/home/jiangbo/agentflow/tmp/build",
        "src_dirs": ["/home/jiangbo/GalSim/src"]
    }
    
    project = CppProject(**config)

    #print(project.find_definition("galsim::Nearest::shoot"))
    print(project.fetch_source_code("galsim::Nearest::shoot"))

def TEST_lenstool_project():
    config = {
        "build_options": ["-I/home/jiangbo/lenstool/include", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],
        "force_build": True,
        "build_dir": "/home/jiangbo/lenstool/build",
        "src_dirs": ["/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"],
        "filter_by_dirs": ["/home/jiangbo/lenstool/include", "/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"]
    }
    project = CppProject(**config)
    #print(project.find_definition("main"))
    call_graph = project.get_call_graph("o_chi_lhood0")
    return
    
def TEST_lenstool_project_fetch_source_code():
    config = {
        "build_options": ["-I/home/jiangbo/lenstool/include", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],
        "force_build": True,
        "build_dir": "/home/jiangbo/lenstool/build",
        "src_dirs": ["/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"],
        "filter_by_dirs": ["/home/jiangbo/lenstool/include", "/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"]
    }
    project = CppProject(**config)
    print(project.fetch_source_code("cubetosou"))

    return

def TEST_lenstool_project_find_definition_by_name():
    config = {
        "build_options": ["-I/home/jiangbo/lenstool/include", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],
        "force_build": True,
        "build_dir": "/home/jiangbo/lenstool/build",
        "src_dirs": ["/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"],
        "filter_by_dirs": ["/home/jiangbo/lenstool/include", "/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"]
    }
    project = CppProject(**config)
    gg = project.find_definition_by_name("dpl_from_kappa")
    def_cursors = project.find_definition_by_name("stf")
    for cursor in def_cursors:
        call_expr_nodes = [node for node in cursor.walk_preorder() \
            if node.kind == CursorKind.CALL_EXPR and node.referenced]
        for call_expr in call_expr_nodes:
            print(call_expr.spelling)    

    print(gg)
    return

def TEST_lenstool_project_fetch_context():
    config = {
        "build_options": ["-I/home/jiangbo/lenstool/include", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],
        "force_build": False,
        "build_dir": "/home/jiangbo/lenstool/build",
        "src_dirs": ["/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"],
        "filter_by_dirs": ["/home/jiangbo/lenstool/include", "/home/jiangbo/lenstool/src", "/home/jiangbo/lenstool/liblt"]
    }
    st = time.time()
    project = CppProject(**config)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")
    context = project.fetch_context("alloc_square_double")
    print(context)

    return

def TEST_ImageMagick_draw_complete_graph():

    config = {
        "build_options": ["-I/usr/lib/gcc/x86_64-linux-gpu/12/include", "-I/media/jiangbo/datasets/ImageMagick"],
        "force_build": False,
        "build_dir": "/media/jiangbo/datasets/ast_cache/ImageMagick",
        "src_dirs": ["/media/jiangbo/datasets/ImageMagick/MagickCore"],
        "filter_by_dirs": ["/media/jiangbo/datasets/ImageMagick/MagickCore"]
    }

    project = CppProject(**config)
    res = project.find_definition_by_name(symbol='DeskewImage')
    project.draw_complete_graph("ImageMagick")

def TEST_ray_tracing_draw_complete_graph():

    config = {
        "build_options": ["-I/usr/lib/gcc/x86_64-linux-gpu/12/include", "-I/media/jiangbo/datasets/raytracing.github.io/src/InOneWeekend"],
        "force_build": False,
        "build_dir": "/media/jiangbo/datasets/ast_cache/raytracing",
        "src_dirs": ["/media/jiangbo/datasets/raytracing.github.io/src/InOneWeekend"],
        "filter_by_dirs": ["/media/jiangbo/datasets/raytracing.github.io/src/InOneWeekend"]
    }

    project = CppProject(**config)
    project.draw_complete_graph("raytracing")

def TEST_ray_tracing_v2_draw_complete_graph():

    config = {
        "build_options": [
            "-xc++", "-std=c++11", 
            "-I/usr/lib/llvm-14/lib/clang/14.0.6/include",
            "-I/usr/lib/gcc/x86_64-linux-gpu/12/include", 
            "-I/media/jiangbo/datasets/raytracing.github.io/src",
            "-I/media/jiangbo/datasets/raytracing.github.io/src/TheNextWeek"
        ],
        "force_build": False,
        "build_dir": "/media/jiangbo/datasets/ast_cache/raytracing",
        "src_dirs": ["/media/jiangbo/datasets/raytracing.github.io/src/TheNextWeek"],
        "filter_by_dirs": ["/media/jiangbo/datasets/raytracing.github.io/src/TheNextWeek"]
    }

    project = CppProject(**config)
    project.draw_complete_graph("raytracingv2_simplified")

def TEST_lenstool_mini_query_graph():
    with MemgraphIngestor(host="localhost", port=7687) as ingestor:
        nodes_query = """
        MATCH (n)
        RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
        """
        nodes_data = ingestor.fetch_all(nodes_query)
        print(json.dumps(nodes_data, indent=4))

def TEST_lenstool_mini_update_graph():
    config = {
        "build_options": ["-I/home/jiangbo/lenstool-cubetosou/include", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],
        "force_build": True,
        "build_dir": "/home/jiangbo/lenstool-cubetosou/build",
        "src_dirs": ["/home/jiangbo/lenstool-cubetosou/src", "/home/jiangbo/lenstool-cubetosou/liblt"],
        "filter_by_dirs": ["/home/jiangbo/lenstool-cubetosou"]
    }
    st = time.time()
    project = CppProject(**config)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(host="localhost", port=7688) as ingestor:    
        ingestor.clean_database()

        for filename, ptu in project.parsed_tus.items():
            for unique_id, clazz in ptu.classes.items():
                clazz_props = {
                    "unique_id": clazz.get_usr(),
                    "qualified_name": CursorUtils.get_full_name(clazz),
                    "name": clazz.spelling,
                    "location_file": clazz.location.file.name,
                    "location_start": clazz.extent.start.line,
                    "location_end": clazz.extent.end.line
                }
                ingestor.ensure_node_batch("Class", clazz_props)

            for unique_id, func in ptu.def_cursors.items():
                func_props = {
                    "unique_id": func.get_usr(),
                    "qualified_name": CursorUtils.get_full_name(func),
                    "name": func.spelling,
                    "location_file": func.location.file.name,
                    "location_start": func.extent.start.line,
                    "location_end": func.extent.end.line
                }    
                ingestor.ensure_node_batch("Function", func_props)
        
        ingestor.flush_nodes()

        for filename, ptu in project.parsed_tus.items():
            for unique_id, func in ptu.def_cursors.items():
                call_exprs = project.get_call_expr_nodes(func, [], unique=True)
                for call_expr in call_exprs:
                    ingestor.ensure_relationship_batch(
                        ("Function", "unique_id", func.get_usr()), 
                        "CALLS",
                        ("Function", "unique_id", call_expr.referenced.get_usr())
                    )

        ingestor.flush_relationships()

        nodes_query = """
        MATCH (n)
        RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
        """
        nodes_data = ingestor.fetch_all(nodes_query)
        print(nodes_data)

        print("===")

        relations_query = """
        MATCH (n:Function)-[r:CALLS]->(m:Function)
        RETURN n.qualified_name as caller_name, m.qualified_name as callee_name
        """

        relations_data = ingestor.fetch_all(relations_query)
        print(relations_data)

        sort_query = "MATCH (t:Function)\n WITH collect(t) AS tasks\n CALL graph_util.topological_sort(\n tasks,\n (u, v) -> {RETURN EXISTS((u)-[:CALLS]->(v));}\n)\n YIELD nodes\n RETURN [n IN nodes | {id: n.id, name: n.name}] AS topological_order "

        sort_query = """
        MATCH p=(n:Function)-[:CALLS]->(m:Function)
        WITH project(p) AS graph
        CALL graph_util.topological_sort(graph) YIELD sorted_nodes
        UNWIND sorted_nodes AS nodes
        RETURN nodes.name;
        """

        sorted_nodes = ingestor.fetch_all(sort_query)
        for node in sorted_nodes:
            print(node)
    
if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == "-d":
        # run_cli()
        pass
    else:     
        #TEST_galsim_project()        
        #TEST_lenstool_project_find_definition_by_name()
        #TEST_lenstool_project_fetch_source_code()
        #TEST_lenstool_project_fetch_context()
        #TEST_lenstool_project_fetch_source_code()
        #TEST_lenstool_mini_query_graph()
        #TEST_lenstool_mini_update_graph()
        #TEST_lenstool_mini_fetch_for_stmt()
        #TEST_ImageMagick_draw_complete_graph()
        #TEST_ray_tracing_draw_complete_graph()
        TEST_ray_tracing_v2_draw_complete_graph()

