from .code_tool import *
from .file_tool import *
from .uml_tool import *
from .shell_tool import *
from autogen_ext.tools.mcp import mcp_server_tools
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
from autogen_ext.tools.mcp import StdioMcpToolAdapter
from typing import List
from rich.console import Console as RichConsole

def print_tools(tools: List[StdioMcpToolAdapter]) -> None:
    """Print available MCP tools and their parameters in a formatted way."""
    console = RichConsole()
    console.print("\n[bold blue]📦 Loaded MCP Tools:[/bold blue]\n")

    for tool in tools:
        # Tool name and description
        console.print(f"[bold green]🔧 {tool.schema.get('name', 'Unnamed Tool')}[/bold green]")
        if description := tool.schema.get('description'):
            console.print(f"[italic]{description}[/italic]\n")

        # Parameters section
        if params := tool.schema.get('parameters'):
            console.print("[yellow]Parameters:[/yellow]")
            if properties := params.get('properties', {}):
                required_params = params.get('required', [])
                for prop_name, prop_details in properties.items():
                    required_mark = "[red]*[/red]" if prop_name in required_params else ""
                    param_type = prop_details.get('type', 'any')
                    console.print(f"  • [cyan]{prop_name}{required_mark}[/cyan]: {param_type}")
                    if param_desc := prop_details.get('description'):
                        console.print(f"    [dim]{param_desc}[/dim]")
        console.print("─" * 60 + "\n")


# Define a mapping of tool names to functions
tool_mapping = {
    "read_file_content": read_file_content,
    "find_definition": find_definition,
    "find_declaration": find_declaration,
    "fetch_source_code": fetch_source_code,
    "fetch_source_code_snippet": fetch_source_code_snippet,
    "get_call_graph": get_call_graph,
    "read_plantuml_file": read_plantuml_file,
    "run_shell_code": run_shell_code,
    "run_python_code": run_python_code,
    "get_cpp_dir_structure": get_cpp_dir_structure,
    "get_dir_structure_with_tree_cmd": get_dir_structure_with_tree_cmd,
    "get_derived_class_of_class": get_derived_class_of_class,
    "get_derived_class_of_function": get_derived_class_of_function,
    "read_function_from_file": read_function_from_file,
    "read_code_from_file": read_code_from_file,
    "file_edit_insert_include_header": file_edit_insert_include_header,
    "file_edit_insert_code_block": file_edit_insert_code_block,
    "file_edit_delete_one_line": file_edit_delete_one_line,
    "file_edit_delete_code_block": file_edit_delete_code_block,
    "file_edit_replace_code_block": file_edit_replace_code_block,
    "file_edit_update_function_definition": file_edit_update_function_definition,
    "file_edit_rollback": file_edit_rollback,
    "file_edit_save": file_edit_save,
    "file_edit_save_to_file": file_edit_save_to_file,
    "file_edit_rollback_files": file_edit_rollback_files,
    "save_code_to_new_file": save_code_to_new_file,
    "run_cmake_and_make": run_cmake_and_make,
    "run_make": run_make,
    "function_dependency_query": function_dependency_query,
    "file_backup" : file_backup,
    "generate_python_uml": generate_python_uml,
    "generate_cpp_uml": generate_cpp_uml,
    "extract_class_names_from_uml": extract_class_names_from_uml,
    "extract_connect_from_uml" : extract_connect_from_uml,
    "extract_class_structure_from_uml": extract_class_structure_from_uml,
    "extract_Inheritance_classes_from_uml": extract_Inheritance_classes_from_uml,
    "query_right_name": query_right_name,
    "query_important_functions": query_important_functions,
    "extract_inter_class_relationship_from_uml": extract_inter_class_relationship_from_uml,
    "show_dir_content": show_dir_content,
    "get_environment": get_environment,
    "write_file": write_file,
    "read_file": read_file,
    "list_directory": list_directory,
    "get_working_directory": get_working_directory,
    "run_command": run_command,
    "create_ast": create_ast,
    "get_ast_status": get_ast_status,
    "glob_search": glob_search,
}

mcp_tool_mapping = {}

async def register_mcp_tools(param: Union[StdioServerParams, StreamableHttpServerParams, SseServerParams]):
    tools = await mcp_server_tools(param)
    print_tools(tools)
    for tool in tools:
        mcp_tool_mapping[tool.schema['name']] = tool        



# __all__ = ["tool_mapping", "mcp_tool_mapping", "register_mcp_tools", "AST"]