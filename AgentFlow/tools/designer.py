from AgentFlow.tools.memgraph.graph_service import MemgraphIngestor
from AgentFlow.tools.project_base import ProjectBase
from AgentFlow.tools.cpp_project import CppProject
from AgentFlow.tools.agents.glm_agent import GlmAgent

import json
import time
from pathlib import Path
DESIGNER_SYSTEM_PROMPT = """
We need to migrate a C language project to the CUDA environment (CUDA version 12.4) function by function to improve performance. Please undertake the following tasks:
- Analyze whether the specified function is suitable for execution on GPU.
- Design a new interface for the function in the CUDA environment. Try not to create new functions/methods, or create as few as possible; try to keep external interfaces (such as public methods, non-static functions, etc.) unchanged, and modified functions/methods can be called within the interfaces.
- Clarify the calling relationships between this function and other related functions.

### Criterion

1. If a function contains complex logic or calls functions that cannot be executed on a GPU (such as file operations, third-party libraries with unknown specific implementations, etc.), please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": ["cpu"],
        "signature": "__host__ <original sigature of the function>",
        "comment": "use the original code directly",
        "calls": ["func", ...]
    }

2. If a function has simple logic, or calls functions from the C standard library for which CUDA provides corresponding implementations (such as malloc, sin, etc.), but lacks parallelism, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": ["cpu", "gpu"],
        "signature": "__host__ __device__ <original sigature of the function>",
        "comment": "The new version of the function suports cpu and cuda. Use the __CUDA_ARCH__ macro to switch cpu/gpu code if necessary",
        "calls": ["func", ...]
    }

3. Similar to the second scenario, but if you are highly confident that this function will only execute on the GPU in the new project, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": ["gpu"],
        "signature": "__device__ <original sigature of the function>",
        "comment": "The new version of the function suports cuda.",
        "calls": ["func", ...]
    }

4. If a function has good parallelism and all its code can be executed on the GPU, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": ["gpu"],
        "signature": "__global__ <original signature of the function>",
        "comment": "the original function will be implemented as a CUDA kernel."
        "calls": ["func", ...]
    }

5. If a function has good parallelism but not all of its code is executed on the GPU, when CUDA-izing this function, it is necessary to launch some kernel function(s) within the function. Please mark the function as follows:    
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": ["cpu"],
        "signature": "__host__ <original signature of the function>",
        "comment": "The original function will be split into several parts, some of which will be implemented as kernel function(s).",
        "calls": ["func", "kernel", ...],
        "new_created_kernels": [
            {"kernel_name": "<kernel name>", "signature": "__global__ <sigature of the new kernel>", "comment": "It implements the functionality of the original function Lines <xx>-<yy>.", "calls": ["func", ...]},
            ...
            {"kernel_name": "<kernel name>", "signature": "__global__ <sigature of the new kernel>", "comment": "It implements the functionality of the original function Lines <xx>-<yy>.", "calls": ["func", ...]}
        ]
    }

6. For other scenarios, please mark the function as follows (We will check it by manual):
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",      
        "runs_on": ["unknown"]
    }

### Output
1. The "signature" and "comment" properties are used to describe how to implement the function in the new project. The "calls" property restricts which functions the function in the new project can call. The elements in the "calls" property must be known function names, unless they are functions you require to be newly created. 
2. The output must be json-formatted:
    ```json
    {
    }
    ```
"""    

CURRENT_DESIGN_TASK = """
### Input
qualified_name: {function_name}
unique_id: {unique_id}

{function_context}
"""

PARTIALLY_COMPLETED_DESIGN = """
### Partially Completed Design
{partially_completed_design}
"""

IMPLEMENT_SYSTEM_PROMPT = """
You are a CUDA programming assistant. Please translate the input function into a CUDA version.

### Translation Criterion
- The interface for the CUDA version has been specified;
- The functions that can be called in the CUDA version have also been specified. You cannot create new functions, but you can use functions from the C/C++ standard library and CUDA libraries;
- The translated code must follow a file organization structure. Whenever possible, place the translated code into the original file (the one containing the code before translation). I will merge the newly generated code you provide into the original file, and if necessary, I will also modify the file extension to .cu.
- The CUDA code should be as complete as possible. Pseudo-code is not allowed. Necessary header file inclusions and declarations must not be omitted. The file-organized code you generate should ideally be compilable.
- The root directory of the project is /home/jiangbo/lenstool-mini. When including header files located within this directory, specify the include path relative to this project root directory.
- If the signature of the translated function changes (including being explicitly marked as __host__, __device__, or __global__), and if a declaration for this function exists, you must also modify the function's declaration to keep it consistent with the function's implementation signature.

### Output
- Each file that houses the newly generated and structured code should be formatted as follows:
```cpp
// filename: <absolute path of the CUDA version file
<source code>
```

- If the specified constraints (such as function interfaces or available functions) are unreasonable, please directly output the reason as follows:
```json
{ "reason": "the detailed reason"}
```
"""

UPDATE_SYSTEM_PROMPT = """
You are an AI programmer who specializes in merging code fragments based on semantics. You are responsible for merging the translated code fragments into the original code files in a semantic-based manner. Follow these rules strictly:
1. **Merge Criteria**:
   - Most importantly, you need to replace the original function with the translated one (including declarations, definitions, etc.).
   - The order of each translated code fragment is random. Please adjust their order according to the content in the original code file.
2. **Output Format**:
```<programming_language, such as cpp, java, python, etc>
// filename: <the absolute path of the original file>
<fully_merged_code>
```
"""

class Designer:
    def __init__(self, *, project: CppProject, ingestor: MemgraphIngestor):
        self.project = project
        self.ingestor = ingestor

    def get_topological_sorted_nodes(self):
        sort_query = """
        MATCH p=(n:Function)-[:CALLS]->(m:Function)
        WITH project(p) AS graph
        CALL graph_util.topological_sort(graph) YIELD sorted_nodes
        UNWIND sorted_nodes AS nodes
        RETURN properties(nodes) AS properties;
        """
        #sort_query = """
        #MATCH (n:Function)
        #OPTIONAL MATCH p=(n)-[:CALLS]->(m:Function)
        #WITH 
        #collect(DISTINCT n) AS all_nodes,
        #collect(DISTINCT p) AS all_paths
        #WITH project({nodes: all_nodes, relationships: [rel IN reduce(r [], p IN all_paths | r + relationships(p)) | rel]}) AS graph
        #CALL graph_util.topological_sort(graph) YIELD sorted_nodes
        #UNWIND sorted_nodes AS nodes
        #RETURN properties(nodes) AS properties;
        #"""
        sorted_nodes = self.ingestor.fetch_all(sort_query)

        return [sorted_node["properties"] for sorted_node in sorted_nodes]

    def get_callees(self, unique_id):
        query = """
        MATCH (n:Function)-[:CALLS]->(m:Function)
        WHERE n.unique_id = '{unique_id}'
        RETURN properties(m) as properties
        """
        callees = self.ingestor.fetch_all(query=query.format(unique_id=unique_id))
        return [callee["properties"] for callee in callees] if callees else []

    def get_callers(self, unique_id):
        query = """
        MATCH (n:Function)-[:CALLS]->(m:Function)
        WHERE m.unique_id = '{unique_id}'
        RETURN properties(n) as properties
        """
        callers = self.ingestor.fetch_all(query=query.format(unique_id=unique_id))
        return [caller["properties"] for caller in callers] if callers else []

    def get_node(self, unique_id):
        query = """
        MATCH (n:Function)
        WHERE n.unique = $unique_id
        RETURN properties(n) as properties
        """
        nodes = self.ingestor.fetch_all(query, params={"unique_id", unique_id})
        return [node["properties"] for node in nodes] if nodes else []

    def get_all_nodes(self):
        query = """
        MATCH (n:Function)
        RETURN properties(n) as properties
        """
        nodes = self.ingestor.fetch_all(query)
        return [node["properties"] for node in nodes] if nodes else []

    def update_node(self, unique_id, properties):
        set_clause = ", ".join([f"n.{k} = ${k}" for k in properties.keys() if k != "unique_id"])
        query = """
        MATCH (n:Function {{unique_id: $unique_id}})
        SET {set_clause}
        RETURN properties(n) as properties
        """    
        updated_nodes = self.ingestor.fetch_all(query.format(set_clause=set_clause), properties)
        self.ingestor.flush_nodes()
        return [updated_node["properties"] for updated_node in updated_nodes] if updated_nodes else []
    
    def construct_graph(self):
        from AgentFlow.tools.cpp_project import CursorUtils
        self.ingestor.clean_database()
        self.ingestor.flush_all()
        nodes = self.get_all_nodes()
        print(nodes)
        for filename, ptu in self.project.parsed_tus.items():
            for unique_id, clazz in ptu.classes.items():
                clazz_props = {
                    "unique_id": clazz.get_usr(),
                    "qualified_name": CursorUtils.get_full_name(clazz),
                    "name": clazz.spelling,
                    "location_file": clazz.location.file.name,
                    "location_start": clazz.extent.start.line,
                    "location_end": clazz.extent.end.line
                }
                self.ingestor.ensure_node_batch("Class", clazz_props)

            for unique_id, func in ptu.def_cursors.items():
                func_props = {
                    "unique_id": func.get_usr(),
                    "qualified_name": CursorUtils.get_full_name(func),
                    "name": func.spelling,
                    "location_file": func.location.file.name,
                    "location_start": func.extent.start.line,
                    "location_end": func.extent.end.line
                }    
                self.ingestor.ensure_node_batch("Function", func_props)
        
        self.ingestor.flush_nodes()

        for filename, ptu in self.project.parsed_tus.items():
            for unique_id, func in ptu.def_cursors.items():
                call_exprs = self.project.get_call_expr_nodes(func, [], unique=True)
                for call_expr in call_exprs:
                    self.ingestor.ensure_relationship_batch(
                        ("Function", "unique_id", func.get_usr()), 
                        "CALLS",
                        ("Function", "unique_id", call_expr.referenced.get_usr())
                    )

        self.ingestor.flush_relationships()
    
    def design(self):
        nodes = self.get_topological_sorted_nodes()
        for node in nodes[::-1]:
            if "runs_on" in node and node["runs_on"]:
                continue
            messages = [{"role": "system", "content": DESIGNER_SYSTEM_PROMPT}]

            unique_id = node["unique_id"]
            qualified_name = node["qualified_name"]
            callees = self.get_callees(unique_id=unique_id)
            context = self.project.fetch_context(usr=unique_id)
            design_task = CURRENT_DESIGN_TASK.format(function_name=qualified_name, unique_id=unique_id, function_context=context)
            if callees:
                partially_completed_design = ""
                for callee in callees:
                    partially_completed_design += f"The function `{callee['qualified_name']}` will be run on {' and '.join(callee['runs_on'])}, and its function signature is designed as {callee['signature']} in the CUDA project. \n"
                     
                partially_completed_design = PARTIALLY_COMPLETED_DESIGN.format(partially_completed_design=partially_completed_design)
                messages.append({"role": "user", "content": design_task + "\n" + partially_completed_design})     
            else:
                messages.append({"role": "user", "content": design_task})     

            print(messages)
            agent = GlmAgent()
            results = agent.chat(messages)
            result = json.loads(results[0]["content"])

            if result["runs_on"][0] == "unknown":
                print(f"design function {qualified_name} failed")
                raise ValueError(f"design function {qualified_name} failed")
            else:
                updated_node = self.update_node(unique_id=unique_id, properties=result)    
                print(updated_node)

    def translate(self):
        nodes = self.get_topological_sorted_nodes()
        for node in nodes[::-1]:
            translate_prompt = self.generate_translation_prompt(node)
            messages = [ {"role": "system", "content": IMPLEMENT_SYSTEM_PROMPT} ]
            messages.append( {"role": "user", "content": translate_prompt} )
            for message in messages:
                print(message["content"])

            agent = GlmAgent()
            result = agent.chat(messages)
            #result = json.loads(results[0])
            for block in result:
                print(block)
            
            self.update_node(node["unique_id"], {"translated": result, "unique_id": node["unique_id"]})    

    def update_files(self):
        nodes = self.get_topological_sorted_nodes()
        translated_files = {}

        for node in nodes[::-1]:
            translated_snippets = node.get("translated", [])
            if translated_snippets:
                for translated_snippet in translated_snippets:
                    filename = translated_snippet.get("filename")
                    if filename:
                        translated_file = translated_files.get(filename)
                        if translated_file:
                            translated_file.append(translated_snippet)
                        else:
                            translated_files[filename] = [translated_snippet]

        for filename, translated_snippets in translated_files.items():                    
            update_prompt = "### File Content before Translation"
            if filename.endswith(".cu"):
                filename = filename[:-len(".cu")] + ".c"
            with open(filename) as f:
                content = f.read()
            update_prompt += f"```cpp\n// filename:{filename}\n{content}\n```"    
            
            update_prompt += "\n### Translated Code Snippets\n"
            update_prompt += f"The file {filename} has the following translated code snippets:\n"
            for translated_snippet in translated_snippets:
                lang, content = translated_snippet["language"], translated_snippet["content"]
                update_prompt += f"```{lang}\n"
                update_prompt += f"// filename: {filename}\n"
                update_prompt += f"{content}\n```"

            messages = [
                {"role": "system", "content": UPDATE_SYSTEM_PROMPT},
                {"role": "user", "content": update_prompt}
            ]    
            agent = GlmAgent()
            result = agent.chat(messages)
            for block in result:
                with open(block["filename"], "w") as f:
                    f.write(block["content"])
                        
    def generate_translation_prompt(self, node):
        callees = self.get_callees(node['unique_id'])
        prompt = "### The objective of your task\n"
        prompt += f"Translate the function {node['qualified_name']} as the following specification:\n"
        prompt += f"- Interface. The new interface of the function is designed as: {node['signature']}\n"
        prompt += f"- Implementation. {node['comment']}\n"
        calls = node.get("calls", [])
        new_created_kernels = node.get("new_created_kernels", [])
        restricted_calls = set(calls)
        restricted_calls.update([new_kernel['kernel_name'] for new_kernel in new_created_kernels])
        restricted_calls = list(restricted_calls)

        if restricted_calls:
            prompt += f"- Constraint. Within the translated function code, invocation of the functions -{', '.join(restricted_calls)}- is permitted, along with library functions associated with C, C++, and CUDA.\n"
        else:
            prompt += f"- Constraint. In the translated function code, you are restricted to calling only library functions associated with C/C++/CUDA.\n"
        
        if new_created_kernels:
            unimplemented = set([new_kernel['kernel_name'] for new_kernel in new_created_kernels]) - set([callee['qualified_name'] for callee in callees])       
            if unimplemented:
                prompt += f"Note the following GPU kernel(s) must also be implemented: {', '.join(list(unimplemented))}\n"
                for name in unimplemented:
                    new_kernel = [new_kernel for new_kernel in new_created_kernels if new_kernel['kernel_name'] == name][0]
                    prompt += f"- {name}:\n"
                    prompt += f"  - Interface. The new kernel interface is designed as: {new_kernel['signature']}\n"
                    prompt += f"  - Implementation. {new_kernel['comment']}\n"
                    calls = new_kernel.get("calls", [])
                    if calls:
                        prompt += f"  - Constraint. Within this kernel code, invocation of the functions -{', '.join(calls)}- is permitted, along with library functions associated with CUDA.\n"
                    else:    
                        prompt += f"  - Constraint. Within this kernel code, you are restricted to calling only library functions associated with CUDA.\n"

        prompt += "### Context before Translation\n"
        inspect_info = self.project.inspect(usr=node['unique_id'])
        _, callees_in_project, type_defs, type_defs_in_project, symbol_def, symbol_decl = (
            inspect_info[key] for key in ("callees", "callees_in_project", "type_defs", "type_defs_in_project", "definition", "declaration")
        )
        if symbol_decl:
            prompt += f"The function {node['qualified_name']} is declared in the file {symbol_decl.extent.start.file.name}\n"
        else:
            prompt += f"The function {node['qualified_name']} has no declaration\n"    
        prompt += f"The function {node['qualified_name']} is defined in the file {symbol_def.extent.start.file.name}. The detailed code will be provided in the later sections.\n"
        if type_defs_in_project:
            prompt += f"The functions {node['qualified_name']} use the following data structure(s):\n"
            for type_def in type_defs_in_project:
                prompt += f"- {type_def.spelling} is defined in the file {type_def.extent.start.file.name}.\n"
        if callees_in_project:
            prompt += f"The function {node['qualified_name']} directly calls the following function(s):\n"        
            for callee_in_project in callees_in_project:
                callee_def = self.project.find_definition_by_cursor(callee_in_project)
                callee_decl = self.project.find_declaration_by_cursor(callee_in_project)
                callee_def_prompt = f"{callee_in_project.spelling} is defined in the file {callee_def.extent.start.file.name}." if callee_def else f"{callee_in_project.spelling} has no definition."
                callee_decl_prompt = f"{callee_in_project.spelling} is declared in the file {callee_decl.extent.start.file.name}." if callee_decl else f"{callee_in_project.spelling} has no declaration."
                prompt += f"- {callee_decl_prompt} {callee_def_prompt}\n"
        if callees:
            prompt += "### Partially Completed Translation\n"        
            prompt += f"The function(s) called by {node['qualified_name']} has been translated already:\n"
            for callee in callees:
                prompt += f"- The translated function {callee['qualified_name']} has the following signature: {callee['signature']}\n"

        prompt += "### Related Code\n"        
        prompt += "Before reading the code, you need to understand all the prompts above. This will enable you to correctly include the relevant header files to access the associated data structures and functions, as well as figure out how to properly translate the related functions.\n"
        prompt += f"The code related to {node['qualified_name']} is listed as follows: \n\n"
        
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
            code_snippets[file_name] = self.project.fetch_code_snippet_from_file(file_name, sorted_method_defs, requires_complete_code=False, requires_line_nos=False)  
        code_snippets = self.project.format_code_snippets(code_snippets)    

        prompt += code_snippets

        return prompt

def translate_lenstool_mini():
    config = {
        "project_root": "/home/jiangbo/lenstool-mini",
        "project_config": {
            "build_options": ["-I/home/jiangbo/lenstool-mini/include", "-I/home/jiangbo/lenstool-mini/liblt", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/"],
            "force_build": False,
            "build_dir": "/home/jiangbo/lenstool-mini/build",
            "src_dirs": ["/home/jiangbo/lenstool-mini/src", "/home/jiangbo/lenstool-mini/liblt"],
            "filter_by_dirs": ["/home/jiangbo/lenstool-mini"]
        },
        "memgraph_config": {
            "host": "localhost",
            "port": 7687
        }
    }
    project_root = config["project_root"]
    project_config = config["project_config"]
    memgraph_config = config["memgraph_config"]

    from git import Repo
    repo = Repo(project_root)
    repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)

        #designer.construct_graph()
        #designer.design()
        #designer.translate()
        designer.update_files()

def translate_lenstool_cubetosou():
    config = {
        "project_root": "/home/jiangbo/lenstool-cubetosou",
        "project_config": {
            "build_options": ["-I/home/jiangbo/lenstool-cubetosou/include", "-I/home/jiangbo/lenstool-cubetosou/liblt", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include/", "-fsyntax-only"],
            "force_build": False,
            "build_dir": "/home/jiangbo/lenstool-cubetosou/build",
            "src_dirs": ["/home/jiangbo/lenstool-cubetosou/src", "/home/jiangbo/lenstool-cubetosou/liblt"],
            "filter_by_dirs": ["/home/jiangbo/lenstool-cubetosou"]
        },
        "memgraph_config": {
            "host": "localhost",
            "port": 7688
        }
    }
    project_root = config["project_root"]
    project_config = config["project_config"]
    memgraph_config = config["memgraph_config"]

    from git import Repo
    repo = Repo(project_root)
    repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)

        #designer.construct_graph()
        designer.design()
        #designer.translate()
        #designer.update_files()

if __name__ == '__main__':
    translate_lenstool_cubetosou()        