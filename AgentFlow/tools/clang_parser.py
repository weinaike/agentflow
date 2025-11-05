from collections import deque
from typing import List, Union, Callable
import json
import os
import time
from clang.cindex import Index, TranslationUnit, Cursor, CursorKind, TypeKind

from AgentFlow.tools.parser_base import ParserBase, TSNode, TSTree

class TypeUtils:
    @staticmethod
    def get_ultimate_type(typ: TypeKind):
        while True:
            if typ.kind in (TypeKind.POINTER, TypeKind.LVALUEREFERENCE):
                typ = typ.get_pointee()
            elif typ.kind in (TypeKind.RVALUEREFERENCE, ):
                typ = typ.get_canonical()
            #elif typ.kind == TypeKind.ELABORATED:
            #    typ = typ.get_declaration()    
            else:
                break
        return typ

    @staticmethod
    def is_builtin_type(typ: TypeKind):
        return typ in [TypeKind.BOOL, TypeKind.CHAR_U, TypeKind.UCHAR, TypeKind.CHAR16, TypeKind.CHAR32, TypeKind.USHORT, TypeKind.UINT, TypeKind.ULONG, TypeKind.ULONGLONG, TypeKind.UINT128, TypeKind.CHAR_S, TypeKind.SCHAR, TypeKind.WCHAR, TypeKind.SHORT, TypeKind.INT, TypeKind.LONG, TypeKind.LONGLONG, TypeKind.INT128, TypeKind.FLOAT, TypeKind.DOUBLE, TypeKind.LONGDOUBLE, TypeKind.NULLPTR, TypeKind.FLOAT128, TypeKind.HALF, TypeKind.IBM128]

class CursorUtils:
    @staticmethod
    def is_class_definition(node):
        return node.is_definition() and node.kind in [CursorKind.CLASS_DECL,
            CursorKind.CLASS_TEMPLATE, CursorKind.STRUCT_DECL, 
            CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION]
    
    @staticmethod
    def get_ancestors(node):
        ancestors = []
        visited = set([node.get_usr()])
        q = deque([node]) if CursorUtils.is_class_definition(node) else deque([])
        while q:
            cursor: Cursor = q.popleft()
            bases = [c.get_definition() or c.type.get_declaration() for c in cursor.get_children() \
                if c.kind == CursorKind.CXX_BASE_SPECIFIER
            ]
            bases = [c for c in bases if c.get_usr() not in visited]
            ancestors.extend(bases)
            q.extend(bases)
            visited.update([c.get_usr() for c in bases])
        return ancestors    

    @staticmethod
    def is_ancestor_of(lhs: Cursor, rhs: Cursor):   
        ancestors = CursorUtils.get_ancestors(rhs)
        return any([lhs.get_usr() == ancestor.get_usr() for ancestor in ancestors])

    @staticmethod
    def get_overridden_method(node):
        overridden_method = None
        if not node.is_virtual_method():
            return overridden_method
        name, sig = node.spelling, node.type.spelling    
        ancestors = CursorUtils.get_ancestors(node.semantic_parent)
        for ancestor in ancestors:
            methods = CursorUtils.get_class_methods(ancestor)
            methods = [method for method in methods if method.is_virtual_method() and 
                       method.spelling == name and method.type.spelling == sig
            ]
            if len(methods) > 0:
                overridden_method = methods[0]
                break
        return overridden_method    

    @staticmethod
    def is_out_of_any_scope(node: Cursor, scope_checkers: List[Callable[[Cursor], bool]]) -> bool:    
        """Determine if a Clang AST node is outside ALL of the specified scopes.

           A node is considered "out of any scope" if it does NOT belong to at least one of the
           scopes defined by the `scope_checkers`. In other words:
            - Returns True if the node is excluded from all checked scopes.
            - Returns False if the node belongs to at least one of the checked scopes.
        """
        for checker in scope_checkers:
            assert callable(checker), f"Scope checker must be callable, got {type(checker).__name__}"

        is_in_at_least_one_scope = any(checker(node) for checker in scope_checkers)
        return not is_in_at_least_one_scope

    @staticmethod
    def extract_non_locals(node: Cursor) -> List[Cursor]:
        def is_out_of_range(a: Cursor, b: Cursor) -> bool:
            if a.location.file.name != b.location.file.name:
                return True    
            astart, aend = a.extent.start, a.extent.end
            bstart, bend = b.extent.start, b.extent.end
            return astart.line > bend.line \
                or (astart.line == bend.line and astart.column > bend.column) \
                or aend.line < bstart.line \
                or (aend.line == bstart.line and aend.column < bstart.column)

        referenced_non_locals = []
        decl_refs = [c.referenced for c in node.walk_preorder() if c.kind == CursorKind.DECL_REF_EXPR]    
        for decl_ref in decl_refs:
            if decl_ref.is_definition():
                if is_out_of_range(decl_ref, node):
                    referenced_non_locals.append(decl_ref)
            else:
                referenced_non_locals.append(decl_ref)
        return list({non_local.get_usr(): non_local for non_local in referenced_non_locals}.values())
                    
    @staticmethod
    def is_callable(node):
        return CursorUtils.is_function(node) or CursorUtils.is_method(node)
    
    @staticmethod
    def is_function(node):
        return node.kind == CursorKind.FUNCTION_DECL or \
            (node.kind == CursorKind.FUNCTION_TEMPLATE and not CursorUtils.is_class_definition(node.semantic_parent)) 
    
    @staticmethod
    def is_method(node):
        return node.kind in [CursorKind.CXX_METHOD, CursorKind.CONSTRUCTOR, CursorKind.DESTRUCTOR] or \
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
        while parent and parent.kind == CursorKind.NAMESPACE:
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
    def get_for_stmts(node: Cursor):
        for_stmts = [c for c in node.walk_preorder() if c.kind == CursorKind.FOR_STMT]
        return for_stmts

    @staticmethod
    def get_callees(node: Cursor, unique=True):
        callees = [c for c in node.walk_preorder() if c.kind == CursorKind.CALL_EXPR and c.referenced]    
        if unique:
            callees = list({c.referenced.get_usr(): c for c in reversed(callees)}.values())[::-1]
        return callees

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
        def _get_inner_class_aux(node):
            assert CursorUtils.is_class_definition(node), "Only class nodes have inner classes"
            inner_classes = [c for c in node.get_children() if CursorUtils.is_class_definition(c)]
            return inner_classes
        all_inner_classes = []    
        task_queue = deque([node])
        while task_queue:
            node = task_queue.popleft()
            inner_classes = _get_inner_class_aux(node)
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
    def __init__(self, tu: TranslationUnit, parsed_time=None, scope_checkers=[]):
        self.tu = tu
        self.parse_time = parsed_time or time.time()
        self.scope_checkers = scope_checkers
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

    def _add_symbols(self, cursors: List[Cursor], target, requires_def):
        if not isinstance(cursors, list):
            cursors = [cursors]
        if requires_def:
            cursors = [cursor for cursor in cursors if cursor.is_definition() or cursor.is_pure_virtual_method()]
        else:
            cursors = [cursor for cursor in cursors if not cursor.is_definition()]
        for cursor in cursors:
            if not self.scope_checkers or not CursorUtils.is_out_of_any_scope(cursor, self.scope_checkers):
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
    def __init__(self, scope_checkers):
        self.scope_checkers = scope_checkers

    def get_include_headers(self, source_file, index=None, args={}):
        index = index or Index.create()
        tu = index.parse(source_file, args=args, options=TranslationUnit.PARSE_SKIP_FUNCTION_BODIES|TranslationUnit.PARSE_INCOMPLETE)
        header_files = set([include.include.name for include in tu.get_includes()])
        return header_files

    def parse(self, filename: str, *, index=None, unsaved_files=None, args=[]):
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
        return ParsedTu(tu, parsed_time, self.scope_checkers)

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

def TEST_ancestors():
    parser = ClangParser([])
    filename = '/home/jiangbo/tmp/derive/main.cpp'
    args = ["-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"]
    ptu: ParsedTu = parser.parse(filename=filename, index=None, args=args)
    bar = ptu.find_class_by_name("Bar")[0]
    print(bar.extent)
    ancestors = CursorUtils.get_ancestors(bar)
    [print(ancestor.extent) for ancestor in ancestors]
    methods = CursorUtils.get_class_methods(bar)
    show = [method for method in methods if method.spelling == 'show'][0]
    od: Cursor = CursorUtils.get_overridden_method(show)
    print(od.type.spelling)

def TEST_destructor():
    parser = ClangParser([])
    filename = '/home/jiangbo/tmp/dtor/main.cpp'
    args = ["-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"]
    ptu: ParsedTu = parser.parse(filename=filename, index=None, args=args)
    ep = ptu.find_definition_by_name("main")[0]
    callees = CursorUtils.get_callees(ep)
    for callee in callees:
        print(callee.spelling)
    print("====")    
    ep = ptu.find_definition_by_name("Add::~Add")[0]
    callees = CursorUtils.get_callees(ep)
    for callee in callees:
        print(callee.spelling)
    print("====")    

if __name__ == '__main__':
    #TEST_MACROS()    
    #TEST_ancestors()
    TEST_destructor()