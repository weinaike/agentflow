from pathlib import Path
from clang_parser import ClangParser
from code_graph import CodeGraph
from typing_extensions import Annotated, List, Dict, Tuple, Union, Any

code_graph: CodeGraph = None
__parser = ClangParser(["-I/usr/lib/gcc/x86_64-linux-gnu/12/include",
                        "-fsyntax-only",
                        "-fno-debug-info",
                        "-w",
                        "-xc++"
                       ])

def construct_code_graph(
    project_dir: Annotated[str, "The root directory of a C/C++ project"], 
    include_dirs: Annotated[List[str], "The include directories where the header files will be searched"] = [],
    source_dirs: Annotated[List[str], "The source files in these directories will be parsed into Translation Units"] =[],
    scopes: Annotated[List[str], "Only functions/methods defined in these directories will be translated"] = [],
    options: Annotated[List[str], "Options which guides the clang to parse the project, e.g., ['-xc++', '-fsyntax-only']... "] = []
) -> str:
    '''
    It parses the specified project into a code graph.
    '''
    include_dirs = ["-I" + dir if not dir.startswith("-I") else dir for dir in include_dirs]
    build_options = include_dirs + options
    scopes = {"dirs": scopes}
    try:
        code_graph = CodeGraph(__parser, project_dir=project_dir, build_options=build_options,
                               src_dirs=source_dirs, scopes=scopes)
        return f"The project `{project_dir}` has been parsed successfully."                       
    except Exception as e:
        return f"It failed to parse the project `{project_dir}`. The following error(s) was encountered: {str(e)}"    
    
def get_code_graph_schema() -> Dict[str, Any]:
    '''
    Returns the schema of the code graph, which explains the meaning of each attribute value of the nodes in the code graph.
    '''
    return code_graph.code_graph_schema

def get_nodes_by_name(name: Annotated[str, "A name of a class, method, function, etc."]) -> List[Dict[str, Any]]:
    '''
    Returns the node(s) of the specified name. This function may return multiple nodes instead of a single one. 
    '''
    return code_graph.get_nodes_by_name(name=name)

def get_node_by_id(node_id: Annotated[str, "the unique identifier of a class, method, function, etc."])->Dict[str, Any]|None:   
    '''Returns the node of the specified ID, or None if the ID doesn't exist in the code graph'''
    node = code_graph.get_node_by_node_id(node_id)
    if node is None:
        return f"The specified node_id `{node_id}` doesn't exist in the code graph. "
    return node   

def get_translation_tasks_topologically(reverse: Annotated[bool, "A boolean parameter to control the topological sorting order"])->List[set]:
    """Topologically sorts the strongly connected components (SCCs) of the graph and returns the sorted SCC list for translation tasks.

    Steps:
    1. Partition the internal graph into multiple strongly connected components (SCCs).
    2. Perform topological sorting on the obtained SCCs.
    3. Return the sorted list of SCCs.

    Returns:
        List[set]: A topologically sorted list of SCCs. Each set in the list represents a group of functions that require translation.
    """
    return code_graph.get_tasks_topologically(reverse)

def get_src_nodes_of(
    node_id: Annotated[str, "id of a node in the graph"], 
    edge_type: Annotated[str, "edge type: CALLS, INHERITS, OVERRIDES, or HAS_METHOD"]
)->List[Dict[str, Any]]:
    """Retrieves the source nodes pointing to the specified node via the given edge type.
    
    Returns a list of dictionaries containing detailed information of the source nodes.
    """
    if edge_type not in ["CALLS", "INHERITS", "OVERRIDES", "HAS_METHOD"]:
        return "ERROR: edge_type must be one of CALLS, INHERITS, OVERRIDES, and HAS_METHOD"

    if not code_graph.graph.has_node(node_id):    
        return f"ERROR: node_id `{node_id}` not found in the graph." 

    return code_graph.get_src_nodes_of(node_id, edge_type)    

def get_dst_nodes_of(
    node_id: Annotated[str, "id of a node in the graph"], 
    edge_type: Annotated[str, "edge type: CALLS, INHERITS, OVERRIDES, or HAS_METHOD"]
)->List[Dict[str, Any]]:
    """Retrieves the destination nodes pointed to by the specified node via the given edge type.
    
    Returns a list of dictionaries containing detailed information of the destination nodes.
    """
    if edge_type not in ["CALLS", "INHERITS", "OVERRIDES", "HAS_METHOD"]:
        return "ERROR: edge_type must be one of CALLS, INHERITS, OVERRIDES, and HAS_METHOD"

    if not code_graph.graph.has_node(node_id):    
        return f"ERROR: node_id `{node_id}` not found in the graph." 

    return code_graph.get_dst_nodes_of(node_id, edge_type)    

def get_file_content(
    filename: Annotated[str, "the absolute path of a file"]
)->str:
    try:
        content = code_graph.get_file_content(filename)
        return content
    except Exception as e:
        return f"read file `{filename} failed: {str(e)}"

def read_code_snippet_from_file(
    filename: Annotated[str, "the absolute path of a file"],
    start: Annotated[Tuple[int, int], "the start location (start-line, start-column) of the code snippet"],
    end: Annotated[Tuple[int, int], "the end location (end-line, end-column) of the code snippet"]
)->str:
    try:
        content = code_graph.get_code_snippet(filename, start, end)        
        return content
    except Exception as e:
        return f"read code snippet from the file `{filename}` failed: {str(e)}"

def insert_initial_translation_plan(
    node_id: Annotated[str, "the id of node in the graph"],
    initial_translation_plan: Annotated[Dict[str, Any], "the translation plan of the specified node(function/method)"]
)->str:
    try:
        node = code_graph.graph.nodes[node_id]        
        node["initial_translation_plan"] = initial_translation_plan
        return "the initial translation plan is inserted successfully"
    except Exception as e:
        return "It failed to insert the initial translation plan"   

def insert_optimized_translation_plan(
    node_id: Annotated[str, "the id of node in the graph"],
    optimized_translation_plan: Annotated[Dict[str, Any], "the translation plan of the specified node(function/method)"]
)->str:
    try:
        node = code_graph.graph.nodes[node_id]        
        node["optimized_translation_plan"] = optimized_translation_plan
        return "the optimized translation plan is inserted successfully"
    except Exception as e:
        return "It failed to insert the optimized translation plan into the specified node."   

def insert_translated_code_snippets(
    node_id: Annotated[str, "the id of node in the graph"],
    code_snippets: Annotated[List[Dict[str, Any]], ""]
)->str:
    try:
        if isinstance(code_snippets, dict):
            code_snippets = [code_snippets]
        for code_snippet in code_snippets:
            if "filename" not in code_snippet:
                return "Error: `filename` is required for each code snippet"    
            if "code_snippet" not in code_snippet:
                return "Error: `code_snippet` is required for each code snippet"    

        node = code_graph.graph.nodes[node_id]
        if "translation_results" not in node:
            node["translation_results"] = []
        node["translation_results"].extend(code_snippets)    
        return "The translated code snippets are inserted successfully"
    except Exception as e:
        return "It failed to insert the translated code snippets into the specified node."
            
def list_files_to_merge() -> List[str]:
    '''
    Lists the files which need to be merged. 
    For each listed file, `get_file_merging_task` can be called to get the file merging task.
    '''
    files_to_merge = []
    for _, node in code_graph.graph.nodes(data=True):
        translation_results = node.get("translation_results", [])
        location = node.get("definition", {}) or node.get("declaration", {})
        original_filename = location.get("file", None)
        for translation_result in translation_results:
            if original_filename:
                translation_result["original_filename"] = original_filename
            translated_filename = translation_result.get("filename", None)    
            if translated_filename:
                if Path(translated_filename).suffix.upper() in [".C", ".CPP", ".CC", ".CXX"]:
                    translated_filename = str(Path(translated_filename).with_suffix(".cu"))
                    translation_result["filename"] = translated_filename
                    files_to_merge.append(translated_filename)
    return files_to_merge                
            

def get_file_merging_task(filename: Annotated[str, "A filename which is from the function `list_files_to_merge`"])->Dict[str, str]:
    ''''''
    original_files = set()
    original_file_content = ""
    translated_code_snippets = ""
    for _, node in code_graph.graph.nodes(data=True):
        translation_results = node.get("translation_results", [])
        for translation_result in translation_results:
            if translation_result["filename"] == filename:
                original_file = translation_result.get("original_filename", None)
                if original_file:
                    original_files.add(original_file)
                translated_code_snippets += f"```cpp\n//filename: {filename}\n{translation_result['code_snippet']}```"    

    for original_file in original_files:
        original_file_content += f"```cpp\n//filename: {original_file}\n{code_graph.get_file_content(original_file)}```"

    return {
        "original_file_content": original_file_content,
        "translated_code_snippets": translated_code_snippets
    }            
