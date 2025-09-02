from collections import deque
from typing import List, Union
import json
import os
import time
from clang.cindex import Index, TranslationUnit, Cursor, CursorKind, TypeKind

from AgentFlow.tools.parser_base import ParserBase, TSNode, TSTree

class TypeUtils:
    @staticmethod
    def get_ultimate_type(kind: TypeKind):
        while True:
            if kind.kind == TypeKind.POINTER:
                kind = kind.get_pointee()
            elif kind.kind in (TypeKind.LVALUEREFERENCE, TypeKind.RVALUEREFERENCE):
                kind = kind.get_canonical()
            else:
                break
        return kind

    @staticmethod
    def is_builtin_type(kind: TypeKind):
        return kind in [TypeKind.BOOL, TypeKind.CHAR_U, TypeKind.UCHAR, TypeKind.CHAR16, TypeKind.CHAR32, TypeKind.USHORT, TypeKind.UINT, TypeKind.ULONG, TypeKind.ULONGLONG, TypeKind.UINT128, TypeKind.CHAR_S, TypeKind.SCHAR, TypeKind.WCHAR, TypeKind.SHORT, TypeKind.INT, TypeKind.LONG, TypeKind.LONGLONG, TypeKind.INT128, TypeKind.FLOAT, TypeKind.DOUBLE, TypeKind.LONGDOUBLE, TypeKind.NULLPTR, TypeKind.FLOAT128, TypeKind.HALF, TypeKind.IBM128]

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
        self.node: Cursor = node
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

    def draw_vis_graph(self, filename, **kwargs):
        from graphviz import Digraph
        from hashlib import md5
        formats = kwargs.get("formats", ["svg"])
        dot = Digraph(comment="call graph")
        dot.attr(rankdir="LR")
        dot.attr("node", shape="box", style='filled', fillcolor='lightblue')
        loop_nodes = kwargs.get("loops", [])
        loop_nodes = set(loop_nodes)
        access_globals_nodes = kwargs.get("access_globals", [])
        access_globals_nodes = set(access_globals_nodes)
        loop_and_access_globals_nodes = loop_nodes & access_globals_nodes

        def select_fillcolor(usr: str):
            if usr in loop_and_access_globals_nodes:
                return "red"
            elif usr in loop_nodes:
                return "yellowgreen"
            elif usr in access_globals_nodes:
                return "cyan"
            else:
                return "lightblue"

        existed_nodes = set()
        existed_edges = set()
        queue = deque([self])
        while queue:
            cg: CallGraph = queue.popleft()
            caller_id = "ID_" + md5(cg.node.get_usr().encode()).hexdigest()[:16]
            fillcolor = select_fillcolor(cg.node.get_usr())
            caller = CursorUtils.get_full_name(cg.node)
            if caller_id not in existed_nodes:
                dot.node(caller_id, caller, fillcolor=fillcolor) 
                existed_nodes.add(caller_id)
            for sub_cg in cg.subgraphs:
                callee_id = "ID_" + md5(sub_cg.node.get_usr().encode()).hexdigest()[:16]
                callee = CursorUtils.get_full_name(sub_cg.node)
                if callee_id not in existed_nodes:
                    fillcolor = select_fillcolor(sub_cg.node.get_usr())
                    dot.node(callee_id, callee, fillcolor=fillcolor)
                    existed_nodes.add(callee_id)
                edge_id = "ID_" + md5((cg.node.get_usr() + sub_cg.node.get_usr()).encode()).hexdigest()[:16]
                if edge_id not in existed_edges:    
                    dot.edge(caller_id, callee_id)
                    existed_edges.add(edge_id)
            queue.extend(cg.subgraphs)    

        try:
            for format in formats:
                dot.format = format
                dot.render(filename, view=False, cleanup=True)    
        except Exception as e:
            print(f"{e}")    
                

class ParsedTu:
    def __init__(self, tu: TranslationUnit, parsed_time=None, filters=[]):
        self.tu = tu
        self.parse_time = parsed_time or time.time()
        self.filters = filters
        self.def_cursors = dict()
        self.decl_cursors = dict()
        self.classes = dict()

        self.extract_symbols()

    @staticmethod
    def extract_macro_definitions(tu):
        '''
        It extracts macro definitions in the translation unit.
        '''
        macro_defs = {}
        inner_tokens = [token for token in tu.cursor.get_tokens()]            
        for i in range(0, len(inner_tokens)-2):
            if inner_tokens[i].spelling == "#" and inner_tokens[i+1].spelling == 'define':
                macro_defs[inner_tokens[i+2].spelling] = inner_tokens[i+2]
        return macro_defs        
        
    def extract_used_macros(self, macro_defs={}):    
        self.used_macros = {}
        inner_macro_defs = ParsedTu.extract_macro_definitions(self.tu)

        inner_macro_defs.update(macro_defs)
        for token in self.tu.cursor.get_tokens():
            macro_def = inner_macro_defs.get(token.spelling, None)
            if macro_def: # the token is a macro
                used_macro = self.used_macros.get(token.spelling, None)
                if used_macro:
                    used_macro.extend( [(token, macro_def)] )
                else:
                    self.used_macros[token.spelling] = [ (token, macro_def) ]

    def extract_symbols(self):
        self.def_cursors, self.decl_cursors = dict(), dict()
        self.classes = dict()
        task_queue = deque([self.tu.cursor])
        while task_queue:
            node = task_queue.popleft()

            namespace_nodes = [child for child in node.get_children() if child.kind == CursorKind.NAMESPACE]
            task_queue.extend(namespace_nodes)

            ## add symbols in the current `node`
            #(1) extract variables
            variable_nodes = [child for child in node.get_children() if child.kind == CursorKind.VAR_DECL]
            self._add_symbols(variable_nodes, self.decl_cursors, False)
            self._add_symbols(variable_nodes, self.def_cursors, True)
            #(2) extract inner classes and methods
            class_nodes = [child for child in node.get_children() if CursorUtils.is_class_definition(child)]
            inner_class_nodes = []
            for class_node in class_nodes:
                inner_class_nodes.extend(CursorUtils.get_inner_classes(class_node))
            class_nodes.extend(inner_class_nodes)    
            self._add_symbols(class_nodes, self.classes, True)
            for class_node in class_nodes:
                method_nodes = CursorUtils.get_class_methods(class_node)
                self._add_symbols(method_nodes, self.decl_cursors, False)
                self._add_symbols(method_nodes, self.def_cursors, True)
            #(3) extract functions
            func_nodes = CursorUtils.get_functions(node)
            self._add_symbols(func_nodes, self.decl_cursors, False)
            self._add_symbols(func_nodes, self.def_cursors, True)

    def _add_symbols(self, cursors, target, requires_def):
        if not isinstance(cursors, list):
            cursors = [cursors]
        if requires_def:
            cursors = [cursor for cursor in cursors if cursor.is_definition()]
        else:
            cursors = [cursor for cursor in cursors if not cursor.is_definition()]
        for cursor in cursors:
            discard = False
            for filter in self.filters:
                if filter(cursor):
                    discard = True    
                    break
            if not discard:
                target[cursor.get_usr()] = cursor    

    def find_definition_by_cursor(self, decl_cursor: Cursor):
        if decl_cursor.is_definition():
            return decl_cursor
        usr = decl_cursor.get_usr()
        return self.def_cursors.get(usr, None)            

    def find_declaration_by_cursor(self, def_cursor: Cursor):
        usr = def_cursor.get_usr()
        return self.decl_cursors.get(usr, None)

    def find_class_by_cursor(self, class_cursor: Cursor):
        usr = class_cursor.get_usr()
        return self.classes.get(usr, None)    

    def find_definition_by_usr(self, usr: str):
        return self.def_cursors.get(usr, None)

    def find_declaration_by_usr(self, usr: str):
        return self.decl_cursors.get(usr, None)    

    def find_class_by_usr(self, usr: str):
        return self.classes.get(usr, None)    
    
    def _find_by_name(self, candidates, target, type=None):    
        target_cursors = []
        for candidate in candidates.values():
            fullname = CursorUtils.get_full_name(candidate)
            name_len = len(target)
            name_matched = False
            if target.startswith("::"):
                if fullname == target[2:]:
                    name_matched = True
            else:
                if name_len == len(fullname):
                    if fullname == target:
                        name_matched = True       
                elif name_len < len(fullname):
                    if fullname[-name_len:] == target and fullname[-(name_len+1)] == ':':
                        name_matched = True     
                
            if name_matched:    
                if type is None or candidate.type.spelling == type:
                    target_cursors.append(candidate)
        return target_cursors                

    def find_definition_by_name(self, name, type=None):
        return self._find_by_name(self.def_cursors, name, type)                

    def find_declaration_by_name(self, name: str, type=None):    
        return self._find_by_name(self.decl_cursors, name, type)                

    def find_class_by_name(self, name, type=None):
        return self._find_by_name(self.classes, name, type)    

    def _get_call_expr_nodes(self, cursor: Cursor, filters=[], unique=False, sort=False):
        '''
        NOTE: return the node with (CursorKind.CALL_EXPR)，rather than (referenced)
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

class ClangParser(ParserBase):
    def __init__(self, filters):
        self.filters = filters

    def get_include_headers(self, source_file, index=None, args={}):
        index = index or Index.create()
        tu = index.parse(source_file, args=args, options=TranslationUnit.PARSE_SKIP_FUNCTION_BODIES|TranslationUnit.PARSE_INCOMPLETE)
        header_files = set([include.include.name for include in tu.get_includes()])
        return header_files

    def parse(self, filename: str, *, index=None, args=[]):
        if filename.endswith(".ast"):
            tu = TranslationUnit.from_ast_file(filename)
            parsed_time = os.path.getctime(filename)
        else:
            if index:
                options = TranslationUnit.PARSE_PRECOMPILED_PREAMBLE
            else:
                options = 0
                index = Index.create()    
            tu = index.parse(filename, args=args, options=options)    
            parsed_time = time.time()
        return ParsedTu(tu, parsed_time, self.filters)

    def get_call_expr_nodes(self, node: Union[TSNode, Cursor], filters=[], unique=False, sort=False) -> Union[List[TSNode], List[Cursor]]:
        call_expr_nodes = [node for node in node.walk_preorder() \
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

def TEST_MACROS():

    parser = ClangParser([])

    #filename = "/home/jiangbo/tmp/macros/test_macros/main.c"
    #args = ["-I/home/jiangbo/tmp/macros/test_macros", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],

    filename = "/home/jiangbo/lenstool-cubetosou/src/keep_cl.c"
    args = ["-I/home/jiangbo/lenstool-cubetosou/include", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"]

    ptu: ParsedTu = parser.parse(filename=filename, index=None, args=args)

    macro_defs = {}
    header_files = set([include.include.name for include in ptu.tu.get_includes()])
    for header_file in header_files:
        h_ptu = parser.parse(header_file, index=None, args=args)
        macro_defs.update(ParsedTu.extract_macro_definitions(h_ptu.tu))    

    ptu.extract_used_macros(macro_defs)

    print(ptu.used_macros)
    print(ptu.used_macros.keys())
    for macro_name, macro_use in ptu.used_macros.items():
        print(f"{macro_name}:")
        for i in macro_use:
            print(f"\t{i[0].extent.start.file.name}:{i[0].extent.start.line}|{i[0].extent.start.column} - {i[1].extent.start.file.name}:{i[1].extent.start.line}|{i[1].extent.start.column}")
        print()    

if __name__ == '__main__':
    TEST_MACROS()    