from collections import deque
from typing import Any, Dict, List, Union, Callable
import json
import os
import time
from clang.cindex import Index, TranslationUnit, Cursor, CursorKind, TypeKind
import networkx as nx
from pyparsing import Diagnostics

from parser_base import ParserBase

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
    def get_parents(node):    
        bases = [c.get_definition() or c.type.get_declaration() for c in node.get_children() \
            if c.kind == CursorKind.CXX_BASE_SPECIFIER
        ]
        return bases

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
    def has_virtual_methods(node: Cursor) -> bool:
        assert CursorUtils.is_class_definition(node), "Must be a class definition."
        methods = CursorUtils.get_class_methods(node)
        for method in methods:
            if method.is_virtual_method():
                return True
        ancestors = CursorUtils.get_ancestors(node)        
        for ancestor in ancestors:
            methods = CursorUtils.get_class_methods(ancestor)
            for method in methods:
                if method.is_virtual_method():
                    return True
        return False            

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

        if not scope_checkers:
            is_in_at_least_one_scope = True  # No scopes to check against, consider it within scope
        else:
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
        #assert CursorUtils.is_class_definition(node), "Only class nodes have methods"
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
            if not CursorUtils.is_class_definition(node):
                return []
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

class ClangParser(ParserBase):
    def __init__(self, args: List[str]=[]):
        self.args = args # arguments for clang parser itself, not for source files

    def get_include_headers(self, source_file, tu, **kwargs):
        if source_file:
            local_kwargs = kwargs.copy()
            local_kwargs['options'] = TranslationUnit.PARSE_SKIP_FUNCTION_BODIES|TranslationUnit.PARSE_INCOMPLETE
            tu, _ = self.parse(source_file, **local_kwargs) # overwrite tu if source_file is given
        header_files = set([include.include.name for include in tu.get_includes()])
        return header_files

    def parse(self, filename: str, **kwargs):
        index = kwargs['index'] if 'index' in kwargs else None
        index = index or Index.create()
        args = kwargs['args'] if 'args' in kwargs else []
        args = self.args + args
        options = kwargs['options'] if 'options' in kwargs else 0 #TranslationUnit.PARSE_PRECOMPILED_PREAMBLE
        unsaved_files = kwargs['unsaved_files'] if 'unsaved_files' in kwargs else None
        tu = None
        if filename.endswith(".ast"): # precompiled AST file
            tu = TranslationUnit.from_ast_file(filename)
            parsed_time = os.path.getctime(filename)
        else:
            # NOTE: it supports parsing memory content via `unsaved_files`
            tu = index.parse(filename, args=args, unsaved_files=unsaved_files, options=options)    
            parsed_time = time.time()
        return tu, parsed_time

class TranslationUnitIngestor:
    """Translation Unit Ingestor
    """
    def __init__(self, graph, scopes=None):
        self.scopes = []
        if scopes:
            dirs = scopes.get("dirs", []) 
            self.scopes.append(
                lambda cursor: any(
                    [cursor.location.file is not None and 
                    os.path.commonpath([dir, cursor.location.file.name]) == dir for dir in dirs]
                )
            )

        self.graph = graph
        
    def ingest_node(self, cursor: Cursor, extra_props: Dict[str, Any]={}):    
        unique_id = cursor.get_usr()
        properties = {
            "unique_id": unique_id,
            "name": cursor.spelling,
            "qualified_name": CursorUtils.get_full_name(cursor),
            "type": "unknown",
            "out_of_scope": False,
        }
        properties.update(extra_props)
        if cursor.extent.start.file is not None:
            location = {
                "file": os.path.abspath(cursor.extent.start.file.name),
                "start": {
                    "line": cursor.extent.start.line, 
                    "column": cursor.extent.start.column
                },
                "end": {
                    "line": cursor.extent.end.line, 
                    "column": cursor.extent.end.column
                }
            }
            properties["definition" if cursor.is_definition() else "declaration"] = location
        if not self.graph.has_node(unique_id):
            self.graph.add_node(unique_id, **properties)
        else:
            self.graph.nodes[unique_id].update(properties)

    def ingest_edge(self, src:Cursor, dst:Cursor, edge_attrs):
        src_id = src.get_usr()
        dst_id = dst.get_usr()
        key = edge_attrs["type"]
        self.graph.add_edge(src_id, dst_id, key=key, **edge_attrs)        
        
    def ingest(self, tu: TranslationUnit):
        cursor_queue = deque([tu.cursor])
        while cursor_queue:
            cursor: Cursor = cursor_queue.popleft()
            namespace_nodes = [child for child in cursor.get_children() if child.kind == CursorKind.NAMESPACE]
            cursor_queue.extend([namespace_node for namespace_node in namespace_nodes \
                if not CursorUtils.is_out_of_any_scope(namespace_node, self.scopes)]
            )
            
            #(1) ingest variables
            variable_cursors = [child for child in cursor.get_children() if child.kind == CursorKind.VAR_DECL]
            for variable_cursor in variable_cursors:
                if not CursorUtils.is_out_of_any_scope(variable_cursor, self.scopes):
                    self.ingest_node(variable_cursor, {"type": "VARIABLE"})

            #(2) ingest classes and methods
            class_cursors = [child for child in cursor.get_children() if CursorUtils.is_class_definition(child) and \
                not CursorUtils.is_out_of_any_scope(child, self.scopes)
            ]
            inner_class_cursors = []
            for class_cursor in class_cursors:
                inner_class_cursors.extend(CursorUtils.get_inner_classes(class_cursor))
            class_cursors.extend(inner_class_cursors)    
            for class_cursor in class_cursors:
                if not CursorUtils.is_out_of_any_scope(class_cursor, self.scopes):
                    self.ingest_node(class_cursor, {"type": "CLASS", "is_pod": class_cursor.type.is_pod()})
                    parents = CursorUtils.get_parents(class_cursor)
                    for parent in parents:
                        self.ingest_edge(class_cursor, parent, {"type": "INHERITS"})
                        out_of_scope = CursorUtils.is_out_of_any_scope(parent, self.scopes)
                        self.ingest_node(parent, {"type": "CLASS", "out_of_scope": out_of_scope, "is_pod": parent.type.is_pod()})
            for class_cursor in class_cursors:
                method_cursors = CursorUtils.get_class_methods(class_cursor)
                for method_cursor in method_cursors:
                    method_type = "CONSTRUCTOR" if method_cursor.kind == CursorKind.CONSTRUCTOR else \
                        "DESTRUCTOR" if method_cursor.kind == CursorKind.DESTRUCTOR else "METHOD"
                    self.ingest_node(method_cursor, {"type": method_type})    
                    self.ingest_edge(class_cursor, method_cursor, {"type": "HAS_METHOD"})
                    callees = CursorUtils.get_callees(method_cursor)
                    for callee in callees:
                        method_type = "CONSTRUCTOR" if callee.referenced.kind == CursorKind.CONSTRUCTOR else \
                            "DESTRUCTOR" if callee.referenced.kind == CursorKind.DESTRUCTOR else "METHOD"
                        if callee.referenced.is_default_constructor() or callee.referenced.is_default_method():
                            # default constructor/method may not have a definition ...
                            self.ingest_node(callee.referenced, {"type": method_type, "is_default": True})
                            self.ingest_edge(callee.referenced.semantic_parent, callee.referenced, {"type": "HAS_METHOD"})
                        self.ingest_edge(method_cursor, callee.referenced, {"type": "CALLS"})
                        out_of_scope = CursorUtils.is_out_of_any_scope(callee.referenced, self.scopes)
                        if out_of_scope:
                            self.ingest_node(callee.referenced, {"type": method_type, "out_of_scope": True})

            #(3) ingest functions/methods and call relations
            func_cursors = [func for func in CursorUtils.get_functions(cursor) if \
                not CursorUtils.is_out_of_any_scope(func, self.scopes)
            ]   
            for func_cursor in func_cursors:
                if CursorUtils.is_function(func_cursor):
                    self.ingest_node(func_cursor, {"type": "FUNCTION"})
                elif CursorUtils.is_method(func_cursor):
                    method_type = "CONSTRUCTOR" if func_cursor.kind == CursorKind.CONSTRUCTOR else \
                        "DESTRUCTOR" if func_cursor.kind == CursorKind.DESTRUCTOR else "METHOD"
                    is_virtual = func_cursor.is_virtual_method()
                    is_pure_virtual = func_cursor.is_pure_virtual_method()
                    self.ingest_node(
                        func_cursor, 
                        {"type": method_type, "is_virtual": is_virtual, "is_pure_virtual": is_pure_virtual}
                    )    
                    if is_virtual:
                        base_method = CursorUtils.get_overridden_method(func_cursor)
                        if base_method:
                            self.ingest_edge(func_cursor, base_method, {"type": "OVERRIDES"})
                callees = CursorUtils.get_callees(func_cursor)
                for callee in callees:
                    self.ingest_edge(func_cursor, callee.referenced, {"type": "CALLS"})
                    out_of_scope = CursorUtils.is_out_of_any_scope(callee.referenced, self.scopes)
                    method_type = "CONSTRUCTOR" if callee.referenced.kind == CursorKind.CONSTRUCTOR else \
                        "DESTRUCTOR" if callee.referenced.kind == CursorKind.DESTRUCTOR else "METHOD"
                    if out_of_scope:
                        self.ingest_node(callee.referenced, {"type": method_type, "out_of_scope": True})

def TEST_TranslationUnitIngestor():
    parser = ClangParser(["-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"])
    filename = '/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu/main.cc'
    tu, _ = parser.parse(filename=filename, index=None, args=[])
    diagnostics = [d for d in tu.diagnostics if d.severity >= Diagnostics.Error]
    if diagnostics:
        for diag in diagnostics:
            print(diag)
    else:
        print("No diagnostics.")        
    graph = nx.MultiDiGraph()    
    ingestor = TranslationUnitIngestor(scopes={"dirs": ["/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"]}, graph=graph)
    ingestor.ingest(tu)
    print(ingestor.graph.number_of_nodes())
    print(ingestor.graph.number_of_edges())

if __name__ == '__main__':
    TEST_TranslationUnitIngestor()
