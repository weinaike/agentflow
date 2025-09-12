from AgentFlow.tools.memgraph.graph_service import MemgraphIngestor
from AgentFlow.tools.project_base import ProjectBase
from AgentFlow.tools.cpp_project import CppProject
from AgentFlow.tools.agents.glm_agent import GlmAgent

import re
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
        "runs_on": 0,
        "requires_translation": 0,
        "signature": "<original sigature of the function>",
        "comment": "use the original code directly",
        "calls": ["func", ...]
    }

2. If a function has simple logic, or calls functions from the C standard library for which CUDA provides corresponding implementations (such as malloc, sin, etc.), but lacks parallelism, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 2,
        "requires_translation": 1,
        "signature": "__host__ __device__ <original sigature of the function>",
        "comment": "The new version of the function suports cpu and cuda. Use the __CUDA_ARCH__ macro to switch cpu/gpu code if necessary",
        "calls": ["func", ...]
    }

3. Similar to the second scenario, but if you are highly confident that this function will only execute on the GPU in the new project, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 1,
        "requires_translation": 1,
        "signature": "__device__ <original sigature of the function>",
        "comment": "The new version of the function suports cuda.",
        "calls": ["func", ...]
    }

4. If a function has good parallelism and all its code can be executed on the GPU, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 3,
        "requires_translation": 1,
        "signature": "__global__ <original signature of the function>",
        "comment": "the original function will be implemented as a CUDA kernel."
        "calls": ["func", ...]
    }

5. If a function has good parallelism but not all of its code is executed on the GPU, when CUDA-izing this function, it is necessary to launch some kernel function(s) within the function. Marking functions that lack for-loop(s) in this format is strictly prohibited. Please mark the function as follows:    
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 0,
        "requires_translation": 1,
        "signature": "<original signature of the function>",
        "comment": "The original function will be split into several parts, some of which will be implemented as kernel function(s).",
        "calls": ["<Function(including the new created kernels) that will be called DIRECTLY by this translated function; If a function is not directly called in the translated version but invoked through a newly created kernel, it should not be listed here; Each qualified function name should be listed as an individual element in this calls list.>", ...],
        "new_created_kernels": [
            {
                "kernel_name": "<kernel name>", 
                "signature": "__global__ <sigature of the new kernel>", 
                "comment": "<Please mark the specific code range in the original function that the current kernel is responsible for implementing (it is sufficient to list the first and last lines of code), and explain why this code range needs to be parallelized.>", 
                "calls": ["function called in this kernel", ...]
            },
            ...
            {
                "kernel_name": "<kernel name>", 
                "signature": "__global__ <sigature of the new kernel>", 
                "comment": "<Please mark the specific code range in the original function that the current kernel is responsible for implementing (it is sufficient to list the first and last lines of code), and explain why this code range needs to be parallelized.>", 
                "calls": ["function called in this kernel", ...]
            }
        ]
    }

6. For other scenarios, please mark the function as follows (We will check it by manual):
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",      
        "runs_on": -1
    }

### Suggestions
1. For functions/methods that call malloc/free, it is recommended to convert them into __host__ __device ones__. Specifically, on the host side, they still call malloc/free, while on the device side, they call cudaMalloc/cudaFree (currently, CUDA already supports calling these two CUDA functions on the device side).

2. It is forbidden to convert functions or code snippets that have no loops or very few loop iterations into CUDA for execution on GPUs, as doing so will instead reduce program performance.

### Output
1. The "signature" and "comment" properties are used to describe how to implement the function in the new project. The "calls" property restricts which functions the function in the new project can call. The elements in the "calls" property must be known function names, unless they are functions you require to be newly created. 
2. The output must be json-formatted:
    ```json
    {
    }
    ```
"""    

REFINE_INTERFACE_SYSTEM_PROMPT = """
You are a CUDA programming assistant. We are translating the code of a project into CUDA. For each function in the project, we have designed their preliminary translated interfaces (not yet implemented). Now, we need to optimize and confirm these interfaces. Your responsibility is to determine whether a function marked as __host__ __device__ or __device__ is reasonable. If it is reasonable, no modification is needed; otherwise, modifications should be made in accordance with the judgment rules.
### Judgment Rules
- Determining whether a function marked as __host__ __device__ or __device__ is reasonable depends on the functions that call this function (hereinafter referred to as "callers", and the function to be judged is referred to as "callee").
- If at least one caller is marked as __host__ __device__ or __device__ in its translated interface, and the caller still directly calls the callee after translation, then it is reasonable for the callee to be marked as __host__ __device__ or __device__.
- If at least one caller is marked as __host__ (or unmarked) in its translated interface, and the caller still directly calls the callee after translation, then it is reasonable for the callee to be marked as __host__ (or unmarked).
- If at least one caller is marked as __host__ (or unmarked) in its translated interface, but after translation, the caller will be split into some kernel functions, and the callee is called in these kernel functions, then it is reasonable for the callee to be marked as __device__.

You need to adjust the mark of the callee based on the above rules and your own experience. The final mark should be one of the following: __host__ __device__, __device__, or unmarked.

### Output
Please output the result in the following JSON format. Among them:
- The value of runs_on can be 0, 1, or 2, which respectively represent "unmarked", "__device__", and "__host__ __device__";
- The value of requires_translation can be 0 or 1. This value is set to 0 only if you think the implementation of the original function can be directly used as the translated implementation; otherwise, it is set to 1;
- signature should be filled with the translated interface signature of the callee;
- comment should briefly describe how the callee is translated.
```json
{
"runs_on": <0, 1, or 2>,
"requires_translation": <0 or 1>,
"signature": "<The translated interface signature of the callee>",
"comment": "<A brief description of how the callee is translated>"
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
- The translated code must follow a file organization structure. Whenever possible, place the translated code into the original file (the one containing the code before translation). If necessary, you should modify the file extension to .cu.
- The CUDA code should be as complete as possible. Pseudo-code is not allowed. Necessary header file inclusions and declarations must not be omitted. The file-organized code you generate should ideally be compilable.
- If you need to include new header files, please first check the Makefile configuration (if existed) to ensure the correct header file paths.
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
   - Before merging, please adjust the order of translated code fragment according to the content in the original code file.
   - During merging, you need to replace the original function with the translated one (including declarations, definitions, etc.).
   - During merging, you need to include necessary header files.
   - During merging, you need to keep other code unchanged as much as possible.
   - After merging, if the merged file contains CUDA code, the file extension should be changed from .c or .cpp to .cu.
2. **Output Format**:
```<programming_language, such as cpp, java, python, etc>
// filename: <the absolute path of the original file, maybe with new file extension>
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
        WHERE n.unique_id = $unique_id
        RETURN properties(n) as properties
        """
        nodes = self.ingestor.fetch_all(query, params={"unique_id": unique_id})
        return [node["properties"] for node in nodes] if nodes else []

    def get_caller_nodes(self, unique_id):
        query = """
        MATCH (n: Function) -[:CALLS]-> (m: Function)
        WHERE m.unique_id = $unique_id
        RETURN properties(n) as properties
        """    
        nodes = self.ingestor.fetch_all(query, params={"unique_id": unique_id})
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
        if "unique_id" not in properties:
            properties["unique_id"] = unique_id
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
            if "runs_on" in node:
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
                    partially_completed_design += f"The function `{callee['qualified_name']}` will be run on {callee['runs_on']}, and its function signature is designed as {callee['signature']} in the CUDA project. \n"
                     
                partially_completed_design = PARTIALLY_COMPLETED_DESIGN.format(partially_completed_design=partially_completed_design)
                messages.append({"role": "user", "content": design_task + "\n" + partially_completed_design})     
            else:
                messages.append({"role": "user", "content": design_task})     

            for message in messages:
                print(message["content"])
            agent = GlmAgent()
            results = agent.chat(messages)
            result = json.loads(results[0]["content"])

            if result["runs_on"] == -1:
                print(f"design function {qualified_name} failed")
                raise ValueError(f"design function {qualified_name} failed")
            else:
                updated_node = self.update_node(unique_id=unique_id, properties=result)    
                print(updated_node)

    def refine_interfaces(self):
        nodes = self.get_topological_sorted_nodes()
        for node in nodes:
            runs_on = node.get("runs_on", -1)
            unique_id = node["unique_id"]
            signature = node["signature"]
            host_signature = re.sub("__device__ ", "", signature)
            host_signature = re.sub("__host__ ", "", host_signature)
            if runs_on not in [1, 2]: # 1: __host__ __device__, 2: __device__
                continue
            caller_nodes = self.get_caller_nodes(node['unique_id'])
            if caller_nodes:
                runs_on_gpu = any([node.get("runs_on", -1) in [1, 2, 3]  for node in caller_nodes])
                if runs_on_gpu:
                    # 前置函数中至少有一个在GPU上执行，该函数的确需要是__device__。无需修改
                    # 这里的判断仍不够严格
                    continue
                nodes_with_new_kernels = [node for node in caller_nodes if "new_created_kernels" in node]
                if nodes_with_new_kernels:
                    task = "### Interface of the function to be judged\n"
                    function_def = self.project.find_definition(node["qualified_name"], requires_lines=False)[node["qualified_name"]][0]["text"]
                    task += "#### Original Implementation\n"
                    task += function_def
                    task += "\n####Preliminary Interface\n"
                    task += """
                    ```json
                    {{
                        "runs_on": {runs_on},
                        "requires_translation: {requires_translation},
                        "signature": {signature},
                        "comment": {comment}
                    }}
                    ```
                    """.format(runs_on=node.get("runs_on", -1), 
                               requires_translation=node.get("requires_translation", 0),
                               signature=node.get("signature", ""),
                               comment=node.get("comment", "")
                    )
                    for node_with_new_kernels in nodes_with_new_kernels:
                        task += f"\n### Interface of the caller {node_with_new_kernels.get('qualified_name')}\n"
                        function_def = self.project.find_definition(node_with_new_kernels["qualified_name"], requires_lines=False)[node_with_new_kernels["qualified_name"]][0]["text"]
                        task += "#### Original Implementation\n"
                        task += function_def
                        task += "\n####Preliminary Interface\n"
                        task += """
                        ```json
                        {{
                            "runs_on": {runs_on},
                            "requires_translation: {requires_translation},
                            "signature": "{signature}",
                            "comment": "{comment}",
                            "new_created_kernels": "{new_created_kernels}"
                        }}
                        ```
                        """.format(runs_on=node_with_new_kernels.get("runs_on", -1), 
                                requires_translation=node_with_new_kernels.get("requires_translation", 0),
                                signature=node_with_new_kernels.get("signature", ""),
                                comment=node_with_new_kernels.get("comment", ""),
                                new_created_kernels=node_with_new_kernels.get("new_created_kernels", [])
                        )
                    messages = [
                        {"role": "system", "content": REFINE_INTERFACE_SYSTEM_PROMPT},
                        {"role": "user", "content": task}
                    ]    

                    for message in messages:
                        print(message["content"])

                    agent = GlmAgent()
                    result = agent.chat(messages)
                    for block in result:
                        self.update_node(unique_id=unique_id, properties=json.loads(block["content"]))
                else:
                    # 没有任何前置函数拆分出kernel，当前函数不需要CUDA版本
                    self.update_node(unique_id=unique_id, properties={
                        "runs_on": 0,
                        "requires_translation": 0,
                        "signature": host_signature,
                        "comment": "copy the original code"
                    })

            else:
                # 没有前置函数，该函数无法在设备上运行
                self.update_node(unique_id=unique_id, properties={
                    "runs_on": 0,
                    "requires_translation": 0,
                    "signature": host_signature,
                    "comment": "copy the original code"
                })
    
    def translate(self):
        nodes = self.get_topological_sorted_nodes()
        for node in nodes[::-1]:
            requires_translation = node.get("requires_translation", 0)
            translated = "translated" in node
            if translated or requires_translation == 0: # skip translated functions
                continue
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
        group_translated_snippets = {}

        for node in nodes[::-1]:
            translated_snippets = node.get("translated", [])
            if translated_snippets:
                for translated_snippet in translated_snippets:
                    translated_filename = translated_snippet.get("filename")
                    if translated_filename:
                        if translated_filename.endswith(".c"):
                            translated_filename += "u"
                        group_translate_snippet = group_translated_snippets.get(translated_filename)
                        if group_translate_snippet:
                            group_translate_snippet.append(translated_snippet)
                        else:
                            group_translated_snippets[translated_filename] = [translated_snippet]

        for translated_filename, translated_snippets in group_translated_snippets.items():                    
            update_prompt = "### File Content before Translation\n"
            original_filename = translated_filename
            if translated_filename.endswith(".cu"):
                original_filename = translated_filename[:-len(".cu")] + ".c"
            with open(original_filename) as f:
                content = f.read()
            update_prompt += f"```cpp\n// filename:{original_filename}\n{content}\n```\n"    
            
            update_prompt += "\n### Translated Code Snippets\n"
            update_prompt += f"The file {translated_filename} has the following translated code snippets:\n"
            for translated_snippet in translated_snippets:
                lang, content = translated_snippet["language"], translated_snippet["content"]
                update_prompt += f"```{lang}\n"
                update_prompt += f"// filename: {translated_filename}\n"
                update_prompt += f"{content}\n```\n"

            messages = [
                {"role": "system", "content": UPDATE_SYSTEM_PROMPT},
                {"role": "user", "content": update_prompt}
            ]    

            for message in messages:
                print(message["content"])

            agent = GlmAgent()
            result = agent.chat(messages)
            for block in result:
                with open(block["filename"], "w") as f:
                    f.write(block["content"])
            #if translated_filename != original_filename:
            #    import os
            #    os.remove(original_filename)        
                        
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

        makefile = self.project.get_makefile()
        prompt += f"### Makefile\n{makefile}"

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
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)

        #designer.construct_graph()
        #designer.design()
        designer.translate()
        #designer.update_files()

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
    #repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)
        #designer.construct_graph()
        #designer.design()
        designer.refine_interfaces()
        #designer.translate()
        #designer.update_files()

if __name__ == '__main__':
    translate_lenstool_cubetosou()        