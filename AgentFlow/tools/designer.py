from AgentFlow.tools.memgraph.graph_service import MemgraphIngestor
from AgentFlow.tools.project_base import ProjectBase
from AgentFlow.tools.cpp_project import CppProject
from AgentFlow.tools.cpp_project import CursorUtils
from AgentFlow.tools.agents.glm_agent import GlmAgent, GPTAgent

from datetime import datetime

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

You first need to determine whether the function to be translated contains a for loop. If the function includes a for loop, you should design the translated interface of the function in accordance with the translation rules for functions with a for loop; if the function does not contain a for loop, you shall design its translated interface in line with the translation rules for functions without a for loop.

#### Translation rules for functions without for loops
1. If a function contains complex logic or calls functions that cannot be executed on a GPU (such as file operations excpet `printf`, third-party libraries with unknown specific implementations, etc.), please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 0,
        "requires_translation": 0,
        "signature": "<original sigature of the function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }
2. If a function itself can be executed on both the CPU and the GPU, and the other functions called by this function can also be executed on both the CPU and the GPU, then this function shall be marked as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 2,
        "requires_translation": 1,
        "signature": "__host__ __device__ <sigature of the function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }
3. If all the translated interfaces of the other functions called within a function are marked as __host__ __device__, or if there are corresponding CUDA API implementations in CUDA for these called functions (fabs, sin, exp, etc., from C standard library), then this function can be migrated to run on the GPU. This function shall be marked as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 2,
        "requires_translation": 1,
        "signature": "__host__ __device__ <sigature of the function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }

#### Translation rules for functions containing for loops

1. If a function contains complex logic (say, hard to decouple data dependency in for-loop) or calls functions that cannot be executed on a GPU (such as file operations excpet `printf`, third-party library functions without known GPU implementation, etc.), please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 0,
        "requires_translation": 0,
        "signature": "<original sigature of the function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }

2. If a function has simple logic, or calls functions from the C standard library for which CUDA provides corresponding implementations (such as malloc, sin, exp, etc.), but lacks parallelism, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 2,
        "requires_translation": 1,
        "signature": "__host__ __device__ <sigature of the function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }

3. Similar to the second scenario, but if you are highly confident that this function will only execute on the GPU in the translated project, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 1,
        "requires_translation": 1,
        "signature": "__device__ <sigature of the translated function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }

4. If a function has good parallelism and all its code can be executed on the GPU, please mark the function as follows:
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 3,
        "requires_translation": 1,
        "signature": "__global__ <signature of the translated function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["func", ...]
    }

5. If a function has good parallelism but not all of its code can be executed on the GPU, when CUDA-izing this function, it is necessary to launch some kernel function(s) within the function. Please mark the function as follows:    
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",
        "runs_on": 0,
        "requires_translation": 1,
        "signature": "<signature of the translated function>",
        "comment": "<Please explain the reason for designing the function signature in this way and detail how to implement the translated function, ensuring that subsequent personnel can successfully complete the specific implementation of the function in accordance with your description.>",
        "calls": ["<Function(including the new created kernels) that will be called DIRECTLY by this translated function; If a function is not directly called in the translated version but invoked through a newly created kernel, it should not be listed here; Each qualified function name should be listed as an individual element in this calls list.>", ...],
        "new_created_kernels": [
            {
                "kernel_name": "<kernel name>", 
                "signature": "__global__ <sigature of the new kernel>", 
                "comment": "<Please mark the specific code range in the original function that the current kernel is responsible for implementing (it is required to list the first and last code between the range), and explain why this code range needs to be parallelized.>", 
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

WARNINGS 
(1) You must make judgments based solely on the function's structure, not your existing general knowledge. In particular, marking functions that lack for-loop(s) in this format is strictly prohibited.
(2) The 'calls' in each element of new_created_kernels refers to the function names callable within the corresponding kernel, while the top-level calls denote the functions callable in the translated function. You must carefully set these 'calls' values, as they affect the signatures of the called functions—particularly whether the signatures require __host__, __host__ __device__, or __device__ qualifiers. Generally, a function being called should not be present in both 'calls' simultaneously.

6. For other scenarios, please mark the function as follows (We will check it by manual):
    {
        "qualified_name": "<the original function name>",
        "unique_id": "<the original unique_id>",      
        "runs_on": -1
    }

### Suggestions
1. For functions/methods that call malloc/free, it is recommended to convert them into __host__ __device__ ones. Specifically, on the host side, they still call malloc/free, while on the device side, they call cudaMalloc/cudaFree (currently, CUDA already supports calling these two CUDA functions on the device side).

2. It is forbidden to convert functions or code snippets that have no loops or very few loop iterations into CUDA for execution on GPUs, as doing so will instead reduce program performance.

3. Device-side code lacks support for variable-length arrays. If an array appears in a function's parameter list, its type must be converted to the corresponding pointer type when designing the converted interface; If a function body contains variable-length arrays, it is recommended that memory be allocated via cudaMalloc when ported to the GPU.

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

### Suggestions
- Variable-length arrays are not supported in device-side code. If a function needs to be executed on the device after translation and uses stack-allocated variable-length arrays internally, during the translation process, consideration should be given to allocating device memory via malloc and freeing the device memory via free at an appropriate time (Note: CUDA already supports calling the malloc and free functions on the device side).
- Pay special attention to the handling of global variables when translating a C/C++ function that uses them to the device side.

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
        WHERE m.out_of_scope = false
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

    def set_property(self, unique_id, name, value):
        query = """
        MATCH (n:Function)
        WHERE n.unique_id = $unique_id
        SET n.{name} = $value
        RETURN properties(n) as properties
        """    
        updated_nodes = self.ingestor.fetch_all(query=query.format(name=name), params={"unique_id": unique_id, "value": value})
        self.ingestor.flush_nodes()
        return [updated_node["properties"] for updated_node in updated_nodes] if updated_nodes else []
    
    def construct_graph(self):
        from hashlib import md5
        class GraphNode:
            def __init__(self, node, fillcolor):
                self.node_id = md5(node.get_usr().encode()).hexdigest()[:8]
                self.node_label = CursorUtils.get_full_name(node)
                #self.node_label = CursorUtils.get_full_displayname(node)
                self.fillcolor = fillcolor
                self.node = node

            def __hash__(self):
                return int(self.node_id, base=16)    

            def __eq__(self, other):
                return self.node_id == other.node_id    
        class GraphEdge:
            def __init__(self, src, dst, color):
                self.src_id = md5(src.get_usr().encode()).hexdigest()[:8]
                self.dst_id = md5(dst.get_usr().encode()).hexdigest()[:8]
                self.color = color        
                self.src_node = src
                self.dst_node = dst

            def __hash__(self):
                return (int(self.src_id, base=16) << 8) + int(self.dst_id, base=16)   

            def __eq__(self, other):
                return self.src_id == other.src_id and self.dst_id == other.dst_id    
        graph_nodes, graph_edges = set(), set()

        self.ingestor.clean_database()
        self.ingestor.flush_all()

        for filename, ptu in self.project.parsed_tus.items():
            for unique_id, clazz in ptu.classes.items():
                clazz_props = {
                    "unique_id": clazz.get_usr(),
                    "qualified_name": CursorUtils.get_full_name(clazz),
                    "name": clazz.spelling,
                    "out_of_scope": CursorUtils.is_out_of_any_scope(clazz, self.project.scope_checkers),
                    "has_virtual_methods": CursorUtils.has_virtual_methods(clazz),
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
                    "out_of_scope": CursorUtils.is_out_of_any_scope(func, self.project.scope_checkers),
                    "is_pure_virtual_method": func.is_pure_virtual_method(),
                    "is_virtual_method": func.is_virtual_method(),
                    "location_file": func.location.file.name,
                    "location_start": func.extent.start.line,
                    "location_end": func.extent.end.line
                }    
                self.ingestor.ensure_node_batch("Function", func_props)
                graph_nodes.add(GraphNode(func, "lightblue" if len(CursorUtils.get_for_stmts(func)) == 0 else "red"))
        
        self.ingestor.flush_nodes()

        for filename, ptu in self.project.parsed_tus.items():
            for unique_id, func in ptu.def_cursors.items():
                if CursorUtils.is_out_of_any_scope(func, self.project.scope_checkers):
                    continue
                if not CursorUtils.is_callable(func):
                    continue
                call_exprs = CursorUtils.get_callees(func, unique=True)
                for_stmts = CursorUtils.get_for_stmts(func)
                call_exprs_in_loop = set()
                for for_stmt in for_stmts:
                    call_exprs_in_this_loop = CursorUtils.get_callees(for_stmt)
                    call_exprs_in_loop.update([c.referenced.get_usr() for c in call_exprs_in_this_loop if c.referenced])
                for call_expr in call_exprs:
                    callee = call_expr.referenced
                    if func.get_usr() == callee.get_usr():
                        continue
                    self.ingestor.ensure_relationship_batch(
                        ("Function", "unique_id", func.get_usr()), 
                        "CALLS",
                        ("Function", "unique_id", callee.get_usr())
                    )
                    edge_color = "red" if callee.get_usr() in call_exprs_in_loop else "black"
                    edge = GraphEdge(func, callee, edge_color)
                    graph_edges.add(edge)
                    # print(f"{edge.dst_id} ==> {CursorUtils.get_full_displayname(edge.dst_node)}")

                    overridden_methods = self.project.get_overridden_methods(callee)
                    for overridden_method in overridden_methods:
                        if func.get_usr() == overridden_method.get_usr():
                            continue
                        self.ingestor.ensure_relationship_batch(
                            ("Function", "unique_id", func.get_usr()), 
                            "CALLS",
                            ("Function", "unique_id", overridden_method.get_usr())
                        )
                        graph_edges.add(GraphEdge(func, overridden_method, edge_color))
                    
                    if CursorUtils.is_out_of_any_scope(callee, self.project.scope_checkers):
                        callee_props = {
                            "unique_id": callee.get_usr(),
                            "qualified_name": CursorUtils.get_full_name(callee),
                            "name": callee.spelling,
                            "out_of_scope": True,
                        }    
                        self.ingestor.ensure_node_batch("Function", callee_props)
                        graph_nodes.add(GraphNode(callee, "gray"))
                            

        self.ingestor.flush_relationships()

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
            filename = "memgraph"
            dot.format = "png"
            dot.render(filename, view=False, cleanup=True)  
            dot.format = "svg"
            dot.render(filename, view=False, cleanup=True)  
        except Exception as e:
            print(e)    
    
    def design(self):
        with open("/home/jiangbo/agentflow/docs/knowledge/DesignKnowledge.json") as f:
            cont = f.read()
            design_knowledge = json.loads(cont)

        nodes = self.get_topological_sorted_nodes()
        total = len(nodes)
        for seq, node in enumerate(nodes[::-1]):
            current_time = datetime.now()
            print(f"[TRACE] {current_time.strftime('%Y%m%d-%H:%M:%S')} Running {node['qualified_name']}... progress: {seq+1}/{total}", flush=True)

            messages = [{"role": "system", "content": DESIGNER_SYSTEM_PROMPT}]

            unique_id = node["unique_id"]
            qualified_name = node["qualified_name"]
            callees = self.get_callees(unique_id=unique_id)
            cursor = self.project.find_definition_by_usr(usr=unique_id)

            context = self.project.fetch_context(usr=unique_id)
            design_task = CURRENT_DESIGN_TASK.format(function_name=qualified_name, unique_id=unique_id, function_context=context)
            guidelines = []
            if callees:
                partially_completed_design = ""
                for callee in callees:
                    callee_prelim_design = callee.get("preliminary_design", None)
                    if callee_prelim_design:
                        partially_completed_design += f"The function `{callee['qualified_name']}` will be run on {callee_prelim_design['runs_on']}, and its function signature is designed as {callee_prelim_design['signature']} in the CUDA project. \n"
                    howto = design_knowledge["function_names"].get(callee["qualified_name"], None) 
                    if howto:
                        guidelines.append(howto)
                partially_completed_design = PARTIALLY_COMPLETED_DESIGN.format(partially_completed_design=partially_completed_design)
                design_task += "\n" + partially_completed_design
            
            if cursor.is_pure_virtual_method():
                howto = design_knowledge["function_types"]["pure_virtual"]    
                guidelines.append(howto)
            elif cursor.is_virtual_method():    
                howto = design_knowledge["function_types"]["virtual"]    
                guidelines.append(howto)

            if guidelines:
                guidelines = "\n".join(guidelines)   
                guidelines = "### Guidelines\n" + guidelines
                design_task += "\n" + guidelines

            messages.append({"role": "user", "content": design_task})
            for message in messages:
                print(message["content"])
            
            preliminary_design         = node.get("preliminary_design")
            preliminary_design_request = node.get("preliminary_design_request")   
            if preliminary_design and messages[-1]["content"] == preliminary_design_request:
                continue
            
            self.set_property(unique_id=unique_id, name="preliminary_design_request", value=messages[-1]["content"])    
            agent = GlmAgent()
            #agent = GPTAgent()
            results = agent.chat(messages)
            result = json.loads(results[0]["content"])

            if result["runs_on"] == -1:
                print(f"design function {qualified_name} failed")
                raise ValueError(f"design function {qualified_name} failed")
            else:
                updated_nodes = self.set_property(unique_id=unique_id, name="preliminary_design", value=result)
                print(updated_nodes)

    def refine_interfaces(self):
        nodes = self.get_topological_sorted_nodes()
        for node in nodes:
            if "refined_design" in node:
                continue
            unique_id = node["unique_id"]
            prelim_design = node.get("preliminary_design", None)
            if not prelim_design:
                raise ValueError(f"please run preliminary_design first: {unique_id}")
            runs_on = prelim_design.get("runs_on", -1)
            signature = prelim_design["signature"]
            host_signature = re.sub("__device__ ", "", signature)
            host_signature = re.sub("__host__ ", "", host_signature)
            if runs_on not in [1, 2]: # 1: __host__ __device__, 2: __device__
                self.set_property(unique_id=unique_id, name="refined_design", value={
                    k:v for k,v in prelim_design.items() if k in ["runs_on", "requires_translation", "signature", "comment"]
                })
                continue
            caller_nodes = self.get_caller_nodes(node['unique_id'])
            if caller_nodes:
                runs_on_gpu = any([caller["refined_design"].get("runs_on", -1) in [1, 2, 3]  for caller in caller_nodes])
                if runs_on_gpu:
                    # 前置函数中至少有一个在GPU上执行，该函数的确需要是__device__。无需修改
                    # 这里的判断仍不够严格
                    self.set_property(unique_id=unique_id, name="refined_design", value={
                        k:v for k,v in prelim_design.items() if k in ["runs_on", "requires_translation", "signature", "comment"]
                    })
                    continue
                callers_with_new_kernels = [caller for caller in caller_nodes if "new_created_kernels" in caller['preliminary_design']]
                if callers_with_new_kernels:
                    task = "### Interface of the function to be judged\n"
                    function_def = self.project.find_definition(node["qualified_name"], requires_lines=False)[node["qualified_name"]][0]["text"]
                    task += "#### Original Implementation\n"
                    task += function_def
                    task += "\n#### Preliminary Interface\n"
                    task += """
                    ```json
                    {{
                        "runs_on": {runs_on},
                        "requires_translation: {requires_translation},
                        "signature": {signature},
                        "comment": {comment}
                    }}
                    ```
                    """.format(runs_on=prelim_design.get("runs_on", -1), 
                               requires_translation=prelim_design.get("requires_translation", 0),
                               signature=prelim_design.get("signature", ""),
                               comment=prelim_design.get("comment", "")
                    )
                    for caller_with_new_kernels in callers_with_new_kernels:
                        caller_qualified_name = caller_with_new_kernels["qualified_name"]
                        caller_prelim_design = caller_with_new_kernels["preliminary_design"]
                        caller_refined_design = caller_with_new_kernels["refined_design"]
                        
                        task += f"\n### Interface of the caller {caller_qualified_name}\n"
                        function_def = self.project.find_definition(caller_qualified_name, requires_lines=False)[caller_qualified_name][0]["text"]
                        task += "#### Original Implementation\n"
                        task += function_def
                        task += "\n#### Preliminary Interface\n"
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
                        """.format(runs_on=caller_refined_design.get("runs_on", -1), 
                                requires_translation=caller_refined_design.get("requires_translation", 0),
                                signature=caller_refined_design.get("signature", ""),
                                comment=caller_refined_design.get("comment", ""),
                                new_created_kernels=caller_prelim_design.get("new_created_kernels", [])
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
                        self.set_property(unique_id=unique_id, name="refined_design", value=json.loads(block["content"]))
                else:
                    # 没有任何前置函数拆分出kernel，当前函数不需要CUDA版本
                    self.set_property(unique_id=unique_id, name="refined_design", value={
                        "runs_on": 0,
                        "requires_translation": 0,
                        "signature": host_signature,
                        "comment": "copy the original code"
                    })

            else:
                # 没有前置函数，该函数无法在设备上运行
                self.set_property(unique_id=unique_id, name="refined_design", value={
                    "runs_on": 0,
                    "requires_translation": 0,
                    "signature": host_signature,
                    "comment": "copy the original code"
                })
    
    def translate(self):
        nodes = self.get_topological_sorted_nodes()
        for node in nodes[::-1]:
            requires_translation = node["refined_design"]["requires_translation"]
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
            
            #self.update_node(node["unique_id"], {"translated": result, "unique_id": node["unique_id"]})    
            self.set_property(unique_id=node["unique_id"], name="translated", value=result)

    def update_files(self):
        nodes = self.get_topological_sorted_nodes()
        group_translated_snippets = {}

        for node in nodes[::-1]:
            translated_snippets = node.get("translated", [])
            if translated_snippets:
                original_filename = node["location_file"]
                for translated_snippet in translated_snippets:
                    translated_filename = translated_snippet.get("filename")
                    translated_snippet["original_filename"] = original_filename
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
            original_filenames = [translated_snippet["original_filename"] for translated_snippet in translated_snippets]
            assert all([original_filename == original_filenames[0] for original_filename in original_filenames])
            original_filename = original_filenames[0]
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
        prelim_design = node["preliminary_design"]
        refined_design = node["refined_design"]
        prompt = "### The objective of your task\n"
        prompt += f"Translate the function {node['qualified_name']} as the following specification:\n"
        prompt += f"- Interface. The new interface of the function is designed as: {refined_design['signature']}\n"
        prompt += f"- Implementation. {refined_design['comment']}\n"
        calls = prelim_design.get("calls", [])
        new_created_kernels = prelim_design.get("new_created_kernels", [])
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
                prompt += f"- The translated function {callee['qualified_name']} has the following signature: {callee['refined_design']['signature']}\n"

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
        prompt += f"### Makefile\nWhen writing code, be sure to refer to the compilation options in the Makefile — especially the -I parameter for specifying header search paths — to avoid errors caused by missing or incorrect header file inclusion.\n{makefile}"

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
        
def TEST_lenstool_mini_fetch_for_stmt():
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

    project.get_for_stmts(usr="c:Bspline.c@F@ft_approx_sin")

def translate_raytracing():
    project_config = {
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
    project_root = "/media/jiangbo/datasets/raytracing.github.io/"
    memgraph_config = {"host": "localhost", "port": 8604}

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
        #designer.refine_interfaces()
        #designer.translate()
        designer.update_files()

def translate_AES():
    project_config = {
        "build_options": [
            "-xc++", "-std=c++11", 
            "-I/usr/lib/llvm-14/lib/clang/14.0.6/include",
            "-I/usr/lib/gcc/x86_64-linux-gpu/12/include", 
        ],
        "force_build": False,
        "build_dir": "/media/jiangbo/datasets/ast_cache/AES",
        "src_dirs": ["/media/jiangbo/datasets/AES/src"],
        "filter_by_dirs": ["/media/jiangbo/datasets/AES/src"]
    }
    project_root = "/media/jiangbo/datasets/AES/"
    memgraph_config = {"host": "localhost", "port": 8700}

    from git import Repo
    repo = Repo(project_root)
    #repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)
        designer.construct_graph()
        #designer.design()
        #designer.refine_interfaces()
        #designer.translate()
        #designer.update_files()

def translate_project3_fof():
    project_config = {
        "build_options": [
            "-xc++", "-std=c++11", 
            "-I/usr/lib/llvm-14/lib/clang/14.0.6/include",
            "-I/usr/lib/gcc/x86_64-linux-gpu/12/include", 
        ],
        "force_build": False,
        "build_dir":       "/media/jiangbo/datasets/ast_cache/project3_fofmain",
        "src_dirs":       ["/media/jiangbo/datasets/ascl.net/repo/project3_FoF-Halo-finder"],
        "filter_by_dirs": ["/media/jiangbo/datasets/ascl.net/repo/project3_FoF-Halo-finder"]
    }
    project_root = "/media/jiangbo/datasets/ascl.net/repo/project3_FoF-Halo-finder"
    memgraph_config = {"host": "localhost", "port": 8700}

    from git import Repo
    repo = Repo(project_root)
    #repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)
        designer.construct_graph()
        # designer.design()
        # designer.refine_interfaces()
        # designer.translate()
        #designer.update_files()

def translate_project6_cjam():
    project_config = {
        "build_options": [
            "-xc++", "-std=c++11", 
            "-I/usr/lib/llvm-14/lib/clang/14.0.6/include",
            "-I/usr/lib/gcc/x86_64-linux-gpu/12/include", 
        ],
        "force_build": False,
        "build_dir":       "/media/jiangbo/datasets/ast_cache/project6_cjam",
        "src_dirs":       ["/media/jiangbo/datasets/ascl.net/repo/project6_CJAM/src"],
        "filter_by_dirs": ["/media/jiangbo/datasets/ascl.net/repo/project6_CJAM"]
    }
    project_root = "/media/jiangbo/datasets/ascl.net/repo/project6_CJAM"
    memgraph_config = {"host": "localhost", "port": 8700}

    from git import Repo
    repo = Repo(project_root)
    #repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)
        designer.construct_graph()
        # designer.design()
        # designer.refine_interfaces()
        # designer.translate()
        #designer.update_files()

def translate_project9_ZENO():
    project_config = {
        "build_options": [
            "-xc++", "-std=c++11", 
            "-I/usr/lib/llvm-14/lib/clang/14.0.6/include",
            "-I/usr/lib/gcc/x86_64-linux-gpu/12/include", 
        ],
        "force_build": False,
        "build_dir":       "/media/jiangbo/datasets/ast_cache/project9_ZENO",
        "src_dirs":       ["/media/jiangbo/datasets/ascl.net/repo/project9_ZENO/src"],
        "filter_by_dirs": ["/media/jiangbo/datasets/ascl.net/repo/project9_ZENO/src"]
    }
    project_root = "/media/jiangbo/datasets/ascl.net/repo/project9_ZENO/"
    memgraph_config = {"host": "localhost", "port": 8700}

    from git import Repo
    repo = Repo(project_root)
    #repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)
        designer.construct_graph()
        # designer.design()
        # designer.refine_interfaces()
        # designer.translate()
        #designer.update_files()

def translate_arctic():
    project_config = {
        "build_options": [
            "-xc++", "-std=c++11", 
            "-I/usr/lib/llvm-14/lib/clang/14.0.6/include",
            "-I/usr/lib/gcc/x86_64-linux-gpu/12/include", 
            "-I/home/jiangbo/arctic/gsl-2.7.1",
            "-I/home/jiangbo/arctic/arctic/include",
        ],
        "force_build": False,
        "build_dir":       "/media/jiangbo/datasets/ast_cache/arctic",
        "src_dirs":       ["/home/jiangbo/arctic/arctic/src", "/home/jiangbo/arctic/arctic/include"],
        "filter_by_dirs": ["/home/jiangbo/arctic/arctic/src", "/home/jiangbo/arctic/arctic/include"]
    }
    project_root = "/home/jiangbo/arctic/arctic"
    memgraph_config = {"host": "localhost", "port": 8700}

    from git import Repo
    repo = Repo(project_root)
    #repo.git.execute(["git", "checkout", "--", "."])

    st = time.time()
    project = CppProject(**project_config, root_dir=project_root)
    et = time.time()
    print(f"It takes {et-st: .3f} second(s) to parse the project")

    with MemgraphIngestor(**memgraph_config) as ingestor:
        designer = Designer(project=project, ingestor=ingestor)
        designer.construct_graph()
        #designer.design()
        # designer.refine_interfaces()
        # designer.translate()
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
            "port": 7690
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
        #designer.refine_interfaces()
        designer.translate()
        #designer.update_files()


        designer.set_property(unique_id="c:Bspline.c@F@deboor_algorithms", name="preliminary_design", value={
    "qualified_name": "deboor_algorithms",
    "unique_id": "c:Bspline.c@F@deboor_algorithms",
    "runs_on": 2,
    "requires_translation": 1,
    "signature": "__host__ __device__ void deboor_algorithms(int p, int k, double u, double *U, double *P, double *s)",
    "comment": "The function contains nested for loops but has data dependencies in the inner loop (d[j] depends on d[j-1]), which limits full parallelization suitable for a __global__ kernel. It uses only basic arithmetic operations supported by CUDA, with no calls to functions incompatible with GPU execution. The variable-length array 'double d[p+1]' must be replaced: on the host, use malloc to allocate a double array of size p+1; on the device, use cudaMalloc (or device - side malloc in CUDA 12.4). The loops retain their structure as the dependencies prevent efficient parallel thread mapping, but the __host__ __device__ qualifier allows execution on both CPU and GPU. The result 'd[p]' is still stored in '*s' as in the original function.",
    "calls": []
        })

if __name__ == '__main__':
    #translate_lenstool_cubetosou()        
    translate_arctic()
    #translate_project6_cjam()