from .code_tool import *
from .file_tool import *
from .uml_tool import *
from .shell_tool import *

# Define a mapping of tool names to functions
tool_mapping = {
    "generate_uml": generate_uml,
    "read_file_content": read_file_content,
    "read_clang_uml_readme_file": read_clang_uml_readme_file,
    "find_definition": find_definition,
    "find_declaration": find_declaration,
    "read_plantuml_file": read_plantuml_file,
    "run_shell_code": run_shell_code,
    "run_python_code": run_python_code,
    "get_dir_structure": get_dir_structure,
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
    "file_edit_update_function_defination": file_edit_update_function_defination,
    "file_edit_rollback": file_edit_rollback,
    "file_edit_save": file_edit_save,
    "save_code_to_new_file": save_code_to_new_file,
    "run_cmake_and_make": run_cmake_and_make,
    "run_make": run_make,
    "function_dependency_query": function_dependency_query,
    "file_backup" : file_backup,
    "generate_python_uml": generate_python_uml,
}

# __all__ = ["tool_mapping"]