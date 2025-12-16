from hashlib import md5
import json
import os
import networkx as nx
import time
from clang.cindex import Index, Cursor, CursorKind, TypeKind
import numpy as np
from typing import List, Union, Dict, Tuple, Any
from collections import deque
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parser_base import ParserBase
from clang_parser import ClangParser, TranslationUnitIngestor

class ParseStatus:
    parse_time: float
    success: bool
    error_msg: str | None

    def __init__(self, parse_time: float, success: bool, error_msg: str | None):
        self.parse_time = parse_time
        self.success = success
        self.error_msg = error_msg

    @staticmethod
    def from_tu(tu, parsed_time):
        diagonostics = [d for d in tu.diagnostics if d.severity >= d.Error]
        return ParseStatus(
            parse_time=parsed_time,
            success=len(diagonostics) == 0,
            error_msg="\n".join([str(d) for d in diagonostics]) if len(diagonostics) > 0 else None
        )

class CodeGraph:
        
    def __init__(self, 
                 parser: ClangParser,
                 project_dir: str,
                 build_options: List[str]=[], 
                 force_build: bool = False,
                 build_dir: str = None,
                 src_dirs: List[str]=[], 
                 scopes: Dict[str, Any] = {},
    ):
        self.parser = parser
        self.project_dir = project_dir

        self.build_options = build_options
        self.force_build = force_build
        self.build_dir = build_dir or os.path.join(project_dir, ".ast_cache")
        self.src_dirs = src_dirs

                
        self.index = Index.create()
        self.graph = nx.MultiDiGraph()
        self.inverse_index = {} # symbol -> set of node ids

        self.ingestor = TranslationUnitIngestor(graph=self.graph, scopes=scopes or {})

        self.source_file_status = {} # build status of each source file

        self.parse()

        self.code_graph_schema = {
            "Node": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "The unique identifier of the node in the graph.", "required": True},
                    "name": {"type": "string", "description": "The name of the node in the graph.", "required": True},
                    "type": {"type": "string", "description": "The type of the node, e.g., FUNCTION, METHOD, CLASS, VARIABLE, CONSTRUCTOR, DESTRUCTOR.", "required": True},
                    "is_pod": {"type": "boolean", "description": "It indicates whether a CLASS node is a POD (plain old data) type", "required": False},
                    "is_virtual": {"type": "boolean", "description": "It indicates whether a METHOD node is a virtual method", "required": False},
                    "is_pure_virtual": {"type": "boolean", "description": "It indicated whether a METHOD node is a pure virtual method", "required": False},
                    "is_default_constructor": {"type": "boolean", "description": "It indicates whether a CONSTRUCTOR node is a default method", "required": False},
                    "out_of_scope": {"type": "boolean", "description": "Indicates whether the node is out of the analyzed scope.", "required": True},

                    "declaration": {"type": "object", "description": "The declaration of the function, method, etc.", "required": False, 
                        "properties": {
                            "file": {"type": "string", "description": "The file where the declaration is located."},
                            "start": {"type": "object", "description": "The start of the declaration.", 
                                "properties": {
                                    "line": {"type": "integer", "description": "The line number (1-based) of the declaration."},
                                    "column": {"type": "integer", "description": "The column number (1-based) of the declaration."}
                                }
                            },
                            "end": {"type": "object", "description": "The end of the declaration.", 
                                "properties": {
                                    "line": {"type": "integer", "description": "The line number (1-based) of the declaration."},
                                    "column": {"type": "integer", "description": "The column number (1-based) of the declaration."}
                                }
                            }
                        }
                    },
                    "definition": {"type": "object", "description": "The definition of the function, method, etc.", "required": False, 
                        "properties": {
                            "file": {"type": "string", "description": "The file where the definition is located."},
                            "start": {"type": "object", "description": "The start of the definition.", 
                                "properties": {
                                    "line": {"type": "integer", "description": "The line number (1-based) of the definition."},
                                    "column": {"type": "integer", "description": "The column number (1-based) of the definition."}
                                }
                            },
                            "end": {"type": "object", "description": "The end of the definition.", 
                                "properties": {
                                    "line": {"type": "integer", "description": "The line number (1-based) of the definition."},
                                    "column": {"type": "integer", "description": "The column number (1-based) of the definition."}
                                }
                            }
                        }
                    },

                    "initial_translation_plan": {
                        "type": "object", "description": "The initial translation plan of the function or method.", "required": False, 
                        "properties": {
                            "signature": {"type": "string", "description": "the signature of the initial plan."},
                            "guide": {"type": "string", "description": "During the porting of C/C++ code to CUDA: if the target function needs to be split into multiple functions, list the signature of each split function in detail and specify their implementation specifications; if no splitting is required, there is no need to list split function signatures, but the implementation specifications for the original function must still be clearly defined. Ensure that other developers can fully understand how to complete the end-to-end porting and implementation of the function from C/C++ to CUDA based on these details."
                            }
                        }
                    },

                    "optimized_translation_plan": {
                        "type": "object", "description": "The optimized translation plan of the function or method.", "required": False, 
                        "properties": {
                            "signature": {"type": "string", "description": "the signature of the translated function/method after ."},
                            "guide": {"type": "string", "description": "During the porting of C/C++ code to CUDA: if the target function needs to be split into multiple functions, list the signature of each split function in detail and specify their implementation specifications; if no splitting is required, there is no need to list split function signatures, but the implementation specifications for the original function must still be clearly defined. Ensure that other developers can fully understand how to complete the end-to-end porting and implementation of the function from C/C++ to CUDA based on these details."
                            }
                        }
                    }, 
                    
                    "translation_results": {
                        "type": "list", "description": "The translation results of the function or method.", "required": False, 
                        "items": {
                            "type": "object",
                            "properties": {
                                "filename": {"type": "string", "description": "The file where the translated function should be located."},
                                "code_snippet": {"type": "string", "description": "The code snippet of the translated function."}
                            }
                        }
                    }
                }
            },

            "Edge": {
                "type": "object",
                "properties": {
                    "from_node": {"type": "string", "description": "The unique identifier of the source node."},
                    "to_node": {"type": "string", "description": "The unique identifier of the target node."},
                    "type": {"type": "string", "description": "CALLS | OVERRIDES | HAS_METHOD | INHERITS"},
                }
            }
        }

    def __hash__(self) -> str:
        if hasattr(self, "md5_hash"):
            return self.md5_hash
        else:
            import hashlib    
            args = []
            args.extend(sorted(list(map(str, self.parser.args))))
            args.extend(sorted(list(map(str, self.build_options))))
            args.extend(sorted(list(map(str, self.src_dirs))))
            key = "::".join(args).encode("utf-8")
            hash_obj = hashlib.sha256(key)
            self.md5_hash = "cpp_" + hash_obj.hexdigest()[:16]
            return self.md5_hash

    def need_parse(self, source_file):
        if self.force_build:
            return True

        last_modified_time = os.path.getmtime(source_file)    
        status: ParseStatus = self.source_file_status.get(source_file, None)    
        if status: # has been loaded into memory
            if status.parse_time < last_modified_time:
                return True
            include_header_files = self.parser.get_include_headers(source_file)
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

                include_header_files = self.parser.get_include_headers(source_file, None)
                for include_header_file in include_header_files:
                    if os.path.getmtime(include_header_file) > last_modified_time:
                        return True
                # the cache file
                tu, parsed_time = self.parser.parse(ast_file, index=self.index)
                self.source_file_status[source_file] = ParseStatus.from_tu(tu, parsed_time)
                self.ingestor.ingest(tu)

                return False
            elif not os.path.exists(ast_file):
                return True

        return False        
    
    def list_source_files(self) -> List[str]:
        source_files = []
        for directory in self.src_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.cpp', '.c', '.cu', '.cc', '.cxx')):
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

        prev_source_files = set(self.source_file_status.keys())
        curr_source_files = set(self.list_source_files())
        for source_file in  prev_source_files - curr_source_files:
            del self.parsed_tus[source_file]
            # TODO: remove nodes and edges from the graph?

        for source_file in curr_source_files:
            ast_file = self._generate_ast_file_name(source_file)
            if self.need_parse(source_file):
                tu, parsed_time = self.parser.parse(filename=source_file, index=self.index, args=[])
                os.makedirs(os.path.dirname(ast_file), exist_ok=True)
                tu.save(ast_file)
                self.source_file_status[source_file] = ParseStatus.from_tu(tu, parsed_time)
                if not self.source_file_status[source_file].success:
                    print(f"Warning: Failed to parse {source_file}:\n{self.source_file_status[source_file].error_msg}")
                self.ingestor.ingest(tu)

        # All have been parsed. Now build the symbol inverse index to speed up the query.        
        self.inverse_index = {}
        for node_id, node_attrs in self.graph.nodes(data=True):
            symbol = node_attrs.get("name", None)
            if symbol:
                if symbol not in self.inverse_index:
                    self.inverse_index[symbol] = set()
                self.inverse_index[symbol].add(node_id)
            symbol = node_attrs.get("qualified_name", None)    
            if symbol:
                if symbol not in self.inverse_index:
                    self.inverse_index[symbol] = set()
                self.inverse_index[symbol].add(node_id)



    def get_nodes_by_name(self, name: str) -> List[Dict[str, Any]]:
        node_ids = self.inverse_index.get(name, set())
        nodes = []
        for node_id in node_ids:
            node_attrs = self.graph.nodes[node_id]
            node_info = {"id": node_id}
            node_info.update(node_attrs)
            nodes.append(node_info)
        return nodes

    def get_node_by_unique_id(self, unique_id: str) -> Dict[str, Any]|None:
        if self.graph.has_node(unique_id):
            node = self.graph.nodes[unique_id]
            return node
        return None

    def has_circular_dependency(self, graph=None) -> bool:
        '''
        Check if the code graph has circular dependencies.
        
        :param self: Description
        :type self: CodeGraph
        :return: True if there are circular dependencies, False otherwise
        :rtype: bool
        '''
        try:
            graph = graph or self.graph
            cycles = list(nx.find_cycle(graph, orientation='original'))
            return len(cycles) > 0
        except nx.NetworkXNoCycle:
            return False    

    def get_subgraph_view(self, node_types: List[str]=[], edge_types: List[str]=[]) -> nx.MultiDiGraph:
        '''
        Get a subgraph view based on specified node and edge types.
        
        :param self: Description
        :type self: CodeGraph
        :param node_types: List of node types to include in the subgraph
        :type node_types: List[str]
        :param edge_types: List of edge types to include in the subgraph
        :type edge_types: List[str]
        :return: A subgraph view of the code graph
        :rtype: nx.MultiDiGraph
        '''
        def node_filter(n):
            if not node_types:
                return True
            node_type = self.graph.nodes[n].get("type", "")
            return node_type in node_types

        def edge_filter(u, v, k):
            if not edge_types:
                return True
            edge_type = self.graph.edges[u, v, k].get("type", "")
            return edge_type in edge_types

        subgraph = nx.subgraph_view(self.graph, filter_node=node_filter, filter_edge=edge_filter)
        return subgraph

    def get_tasks_topologically(self, reverse: bool=True) -> List[set]:        
        '''
        Get tasks in topological order based on function/method call dependencies. 
        Note in order to handle cycles, strongly connected components are treated as single nodes.
        
        :param self: A CodeGraph
        :param reverse: Whether to return the order in reverse
        :type reverse: bool
        :return: A list of sets, each set contains node IDs that form a strongly connected component. Each element in the set is a unique_id of a function/method node.
        :rtype: List[set]
        '''
        subgraph = self.get_subgraph_view(
            node_types=["FUNCTION", "METHOD", "CONSTRUCTOR", "DESTRUCTOR"],
            edge_types=["CALLS"]
        )
        condensed_graph = nx.condensation(subgraph)
        scc_topo_order = list(nx.topological_sort(condensed_graph))
        scc_topo_sets = [condensed_graph.nodes[scc_id]['members'] for scc_id in scc_topo_order]
        if reverse:
            scc_topo_sets.reverse()
        return scc_topo_sets

    def get_src_nodes_of(self, dst_unique_id: str, edge_type: str) -> List[Dict[str, Any]]:
        '''
        Docstring for get_src_nodes_of
        
        :param self: Description
        :param dst_unique_id: Description
        :type dst_unique_id: str
        :param edge_type: Description
        :type edge_type: str
        :return: Description
        :rtype: List[Dict[str, Any]]
        '''
        assert edge_type in ["CALLS", "INHERITS", "OVERRIDES", "HAS_METHOD"]
        srcs = []
        if not self.graph.has_node(dst_unique_id):
            return srcs
        
        for pred in self.graph.predecessors(dst_unique_id):
            for key in self.graph[pred][dst_unique_id]:
                edge_data = self.graph[pred][dst_unique_id][key]
                if edge_data.get("type", "") == edge_type:
                    node = self.graph.nodes[pred]
                    srcs.append(node)
        return srcs

    def get_dst_nodes_of(self, src_unique_id: str, edge_type: str) -> List[Dict[str, Any]]:
        assert edge_type in ["CALLS", "INHERITS", "OVERRIDES", "HAS_METHOD"]
        dsts = []    
        if not self.graph.has_node(src_unique_id):
            return dsts
        
        for succ in self.graph.successors(src_unique_id):
            for key in self.graph[src_unique_id][succ]:
                edge_data = self.graph[src_unique_id][succ][key]
                if edge_data.get("type", "") == edge_type:
                    node = self.graph.nodes[succ]
                    dsts.append(node)
        return dsts    

    def get_callers_of(self, function_unique_id: str) -> List[Dict[str, Any]]:
        '''
        Get all caller nodes of a given function/method node.
        
        :param self: Description
        :type self: CodeGraph
        :param function_node_id: The unique ID of the function/method node
        :type function_node_id: str
        :return: A list of caller node information dictionaries
        :rtype: List[Dict[str, Any]]
        '''
        callers = []
        if not self.graph.has_node(function_unique_id):
            return callers
        
        for pred in self.graph.predecessors(function_unique_id):
            for key in self.graph[pred][function_unique_id]:
                edge_data = self.graph[pred][function_unique_id][key]
                if edge_data.get("type", "") == "CALLS":
                    node_attrs = self.graph.nodes[pred]
                    node_info = {}
                    node_info.update(node_attrs)
                    callers.append(node_info)
        return callers

    def get_callees_of(self, function_unique_id: str) -> List[Dict[str, Any]]:
        '''
        Get all callee nodes of a given function/method node.
        
        :param self: Description
        :type self: CodeGraph
        :param function_node_id: The unique ID of the function/method node
        :type function_node_id: str
        :return: A list of callee node information dictionaries
        :rtype: List[Dict[str, Any]]
        '''
        callees = []
        if not self.graph.has_node(function_unique_id):
            return callees
        
        for succ in self.graph.successors(function_unique_id):
            for key in self.graph[function_unique_id][succ]:
                edge_data = self.graph[function_unique_id][succ][key]
                if edge_data.get("type", "") == "CALLS":
                    node_attrs = self.graph.nodes[succ]
                    node_info = {}
                    node_info.update(node_attrs)
                    callees.append(node_info)
        return callees    

    def get_ancessors_of(self, node_id: str, walk_steps: int = 1) -> List[Dict[str, Any]]:    
        '''
        Get all ancestor nodes of a given node within specified walk steps.
        
        :param self: Description
        :type self: CodeGraph
        :param node_id: The unique ID of the node
        :type node_id: str
        :param walk_steps: Number of steps to walk up the graph
        :type walk_steps: int
        :return: A list of ancestor node information dictionaries
        :rtype: List[Dict[str, Any]]
        '''
        ancestors = set()
        if not self.graph.has_node(node_id) or walk_steps <= 0 or self.graph.nodes[node_id].get("type", "") != "CLASS":
            return ancestors
        
        queue = deque()
        queue.append((node_id, 0))
        
        while queue:
            current_node, current_step = queue.popleft()
            if current_step >= walk_steps:
                continue
            
            for succ in self.graph.successors(current_node):
                for key in self.graph[current_node][succ]:
                    edge_data = self.graph[current_node][succ][key]
                    if edge_data.get("type", "") == "INHERITS":
                        if succ not in ancestors:
                            ancestors.add(succ)
                            queue.append((succ, current_step + 1))
        
        return ancestors

    def get_descendants_of(self, node_id: str, walk_steps: int = 1) -> List[Dict[str, Any]]:    
        '''
        Get all descendant nodes of a given node within specified walk steps.
        
        :param self: Description
        :type self: CodeGraph
        :param node_id: The unique ID of the node
        :type node_id: str
        :param walk_steps: Number of steps to walk down the graph
        :type walk_steps: int
        :return: A list of descendant node information dictionaries
        :rtype: List[Dict[str, Any]]
        '''
        descendants = set()
        if not self.graph.has_node(node_id) or walk_steps <= 0 or self.graph.nodes[node_id].get("type", "") != "CLASS":
            return descendants
        
        queue = deque()
        queue.append((node_id, 0))
        
        while queue:
            current_node, current_step = queue.popleft()
            if current_step >= walk_steps:
                continue
            
            for pred in self.graph.predecessors(current_node):
                for key in self.graph[pred][current_node]:
                    edge_data = self.graph[pred][current_node][key]
                    if edge_data.get("type", "") == "INHERITS":
                        if pred not in descendants:
                            descendants.add(pred)
                            queue.append((pred, current_step + 1))
        
        return descendants    

    def get_file_content(self, filename: str)-> str:
        '''
        Get the entire content of a file.
        
        :param self: Description
        :type self: CodeGraph
        :param filename: the path to the file
        :type filename: str
        :return: Description
        :rtype: str
        '''
        with open(filename, "r") as f:
            return f.read()
        
    def get_code_snippet(self, filename: str, start: Tuple[int, int]|None, end: Tuple[int, int]|None) -> str:    
        '''
        Get the content of a file between the specified start and end positions. If start or end is None, return the entire file content.
        
        :param self: Description
        :type self: CodeGraph
        :param filename: the path to the file
        :type filename: str
        :param start: A 2-tuple representing the (line, column) of the start position
        :type start: Tuple[int, int] | None
        :param end: A 2-tuple representing the (line, column) of the end position
        :type end: Tuple[int, int] | None
        :return: Description
        :rtype: str
        '''
        if start is None or end is None:
            with open(filename, "r") as f:
                return f.read()
        with open(filename, "r") as f:
            lines = f.readlines()
        total_lines = len(lines)
        
        start_line_idx = start[0] - 1
        start_col_idx = start[1] - 1
        end_line_idx = end[0] - 1
        end_col_idx = end[1] - 1
        
        if start_line_idx < 0 or end_line_idx >= total_lines:
            raise IndexError(
                f"Line number out of range: The file has a total of {total_lines} lines, start line {start[0]}, end line {end[0]}"
            )
        if start_line_idx > end_line_idx:
            raise IndexError(f"The start line {start[0]} is greater than the end line {end[0]}")    
        
        start_line_content = lines[start_line_idx]
        prefix_chars = start_line_content[:start_col_idx]
        if all(char.isspace() for char in prefix_chars):
            adjusted_start_col = 0  
        else:
            adjusted_start_col = start_col_idx  
        
        content_parts = []
        if start_line_idx == end_line_idx:
            end_col = min(end_col_idx, len(start_line_content))  # 防止列号超出行长度
            line_content = start_line_content[adjusted_start_col:end_col]
            content_parts.append(line_content)
        else:
            start_line_part = start_line_content[adjusted_start_col:]
            content_parts.append(start_line_part)
            
            for line_idx in range(start_line_idx + 1, end_line_idx):
                content_parts.append(lines[line_idx])
            
            end_line_content = lines[end_line_idx]
            end_col = min(end_col_idx, len(end_line_content))  # 防止列号超出行长度
            end_line_part = end_line_content[:end_col]
            content_parts.append(end_line_part)
        
        return ''.join(content_parts)    


def TEST_ray_tracing_draw_complete_graph():

    parser_args = ["-I/usr/lib/gcc/x86_64-linux-gnu/12/include"]
    parser = ClangParser(args=parser_args)
    config = {
        "build_options": ["-I/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"],
        "force_build": False,
        "src_dirs": [
            "/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"
        ],
        "scopes": {
            "dirs": ["/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"]
        }
    }

    cg = CodeGraph(parser, project_dir=config["src_dirs"][0], **config)
    node_infos = cg.get_nodes_by_name("main")
    for node_info in node_infos:
        location = node_info.get("definition", None) or node_info.get("declaration", None)
        if location:
            filename = location.get("file", "")
            start, end = location.get("start", {}), location.get("end", {})
            start = (start.get("line", 0), start.get("column", 0))
            end = (end.get("line", 0), end.get("column", 0))
            content = cg.get_code_snippet(filename, start, end)
            print(f"--- Node ID: {node_info['id']} ---")
            print(content)
            print("------------------------------")
        break

    tasks = cg.get_tasks_topologically()
    #print(tasks)

    nodes = cg.get_nodes_by_name("camera")
    for node in nodes:
        if node["type"] != "CLASS":
            continue
        print(f"Class metadata for {node['name']}: {node}")
        print(f"Class {node['name']} methods:")
        for succ in cg.graph.successors(node["id"]):
            for key in cg.graph[node["id"]][succ]:
                edge_data = cg.graph[node["id"]][succ][key]
                if edge_data.get("type", "") == "HAS_METHOD":
                    method_node = cg.graph.nodes[succ]
                    print(f"- {method_node.get('name', '')} (ID: {succ})")
        print("------------------------------")

    nodes = cg.get_nodes_by_name("lambertian")
    for node in nodes:
        if node["type"] == "CLASS":
            ancestors = cg.get_ancessors_of(node["id"], walk_steps=2)
            print(f"Ancestors of class {node['name']}:")
            for ancestor_id in ancestors:
                ancestor_node = cg.graph.nodes[ancestor_id]
                print(f"- {ancestor_node.get('name', '')} (ID: {ancestor_id})")
            print("------------------------------")

    nodes = cg.get_nodes_by_name("material")
    for node in nodes:
        if node["type"] == "CLASS":
            descendants = cg.get_descendants_of(node["id"], walk_steps=2)
            print(f"Descendants of class {node['name']}:")
            for descendant_id in descendants:
                descendant_node = cg.graph.nodes[descendant_id]
                print(f"- {descendant_node.get('name', '')} (ID: {descendant_id})")
            print("------------------------------")

    nodes = cg.get_nodes_by_name("scatter")
    for node in nodes:
        print(node)

    nodes = cg.get_nodes_by_name("camera::ray_color")
    for node in nodes:
        callers = cg.get_callers_of(node["id"])
        print(f"Callers of function {node['name']}:")
        for caller in callers:
            print(f"- {caller.get('name', '')} (ID: {caller.get('unique_id', '')})")
        print("------------------------------")

        callees = cg.get_callees_of(node["id"])
        print(f"Callees of function {node['name']}:")
        for callee in callees:
            print(f"- {callee.get('name', '')} (ID: {callee.get('unique_id', '')}) (qualified_name: {callee.get('qualified_name', '')})")        

def TEST_edge_retrieval():
    parser_args = ["-I/usr/lib/gcc/x86_64-linux-gnu/12/include"]
    parser = ClangParser(args=parser_args)
    config = {
        "build_options": ["-I/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"],
        "force_build": False,
        "src_dirs": [
            "/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"
        ],
        "scopes": {
            "dirs": ["/media/jiangbo/datasets/raytracing.github.io/artifacts/raytracing/cpu"]
        }
    }

    cg = CodeGraph(parser, project_dir=config["src_dirs"][0], **config)
    node_infos = cg.get_nodes_by_name("camera::render")    
    for node in node_infos:
        dst_nodes = cg.get_dst_nodes_of(node['unique_id'], 'CALLS')
        for dst_node in dst_nodes:
            print(dst_node)
            print()
        
if __name__ == '__main__':
    #TEST_ray_tracing_draw_complete_graph()
    TEST_edge_retrieval()

