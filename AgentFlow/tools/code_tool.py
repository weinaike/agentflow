
import os
import subprocess
from typing_extensions import Annotated, List, Union
import re
from .file_edit import FileEditClass
from .abstract_syntax_tree import AST
import json

   
def find_definition(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                    class_name:Annotated[str, "The class name to which the function or variable belongs."] = None) -> dict:
    """
    通过C++代码的抽象语法树，查找函数或变量的定义。
    例如：
        若需要查询函数PhotonArray::addTo的定义, 符号为'addTo', 其所属类为'PhotonArray'：
        因而调用方式为
        find_definition("addTo", "PhotonArray")
    """
    ast = AST()
    return ast.find_definition(symbol, class_name)

def find_declaration(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                     class_name:Annotated[str, "The class name to which the function or variable belongs."] = None)-> dict:
    '''
    通过C++代码的抽象语法树，查询函数或者变量的声明。如果查询声明未找到结果，可直接查询定义替代。
    例如：
        若需要查询函数Bounds的声明, 符号为'Bounds'：
        因而调用方式为
        find_declaration("Bounds")
    '''
    
    ast = AST()
    return ast.find_declaration(symbol, class_name)

def fetch_source_code(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                     class_name:Annotated[str, "The class name to which the function or variable belongs."] = None)-> dict:
    '''
    通过C++代码的抽象语法树，查询函数及其调用的相关代码。
    例如：
        若需要查询函数Bounds及其调用函数的相关代码, 符号为'Bounds'：
            fetch_source_code("Bounds")
        若需要查询galsim::SBVonKarman::SBVonKarmanImpl::shoot方法及其调用的相关代码，符号为'shoot', class_name为'galsim::SBVonKarman::SBVonKarmanImpl'
            fetch_source_code("shoot", "galsim::SBVonKarman::SBVonKarmanImpl')    
    '''
    
    ast = AST()
    return ast.fetch_source_code(symbol, class_name)

def get_call_graph(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                     class_name:Annotated[str, "The class name to which the function or variable belongs."] = None)-> dict:
    '''
    通过C++代码的抽象语法树，查询函数的调用图。
    例如：
        若需要查询函数Bounds的声明, 符号为'Bounds'：
            get_call_graph("Bounds")
        若需要查询galsim::SBVonKarman::SBVonKarmanImpl::shoot方法的调用图，符号为'shoot', class_name为'galsim::SBVonKarman::SBVonKarmanImpl'
            get_call_graph("shoot", "galsim::SBVonKarman::SBVonKarmanImpl')    
    '''
    
    ast = AST()
    call_graph = ast.get_call_graph(symbol, class_name)
    return call_graph.to_string(remove_leaf_nodes=True, requires_signature=False)

############ 查询功能 #########

def read_code_from_file(filename: str)->str:
    '''
    Function to read code from a file
    params:
        filename: the file to read the code from

    returns:
        str: the content of the file
        exception: if an exception occurred while reading the file
    '''
    fe = FileEditClass()
    return fe.read_code_from_file(filename)

def read_function_from_file(filename: str, function_name: str)->str:
    '''
    Function to read a function from a file
    params:
        filename: the file to read the function from
        function_name: the function name to read

    returns:
        str: the content of the function
        exception: if an exception occurred while reading the file

    '''
    fe = FileEditClass()
    return fe.read_function_from_file(filename, function_name)


def find_function_range(filename: Annotated[str, "the file to locate the function"],
                        function_name: Annotated[str, "the function name to locate"])->tuple[int, int]:
    '''
    file edit:  Function to find the range of a function in a cpp/h file
    params:
        filename: the file to locate the function
        function_name: the function name to locate

    returns:
        start_line: the start line number of the function (1-indexed)
        end_line: the end line number of the function (1-indexed)

    example:
        find_function_range('path_to_file/file.cpp', 'Position& operator=(const Position<T>& rhs)')

        # Returns (64, 69) if the function is found
        # Returns (None, None) if the function is not found
    '''
    fe = FileEditClass()
    return fe.find_function_range(filename, function_name)

############ 新建文件 #########
def save_code_to_new_file(filename:Annotated[str, "the file to save the code"],
                            code: Annotated[str, "code to save"])->str:
    '''
    file edit: Function to save a code block to a new file
    params:
        filename: the file to save the code to
        code_block: the code block to save

    returns:
        success: if the code block was successfully saved

    example:
        save_code_to_file('path_to_file/file.cpp', """
            #include <iostream>
            int main()
            {
                std::cout << "Hello, World!" << std::endl;
                return 0;
            }
        """)
        save_code_to_file('file.cpp', ['#include <iostream>', 'int main()', '{', '    std::cout << "Hello, World!" << std::endl;', '    return 0;', '}'])
    '''    
    fe = FileEditClass()
    return fe.save_code_to_new_file(filename, code)





####### 编辑功能 ###########
def file_edit_insert_include_header(filename:Annotated[str, "the file to insert the include statement"],
                            include_statement: Annotated[str, "include statement to insert"])->str:
    '''
    file edit: Function to insert an include statement in a file for cpp or h files
    params:
        filename: the file to insert the include statement
        include_statement: include statement to insert

    returns:
        success: if the include statement was successfully inserted
        
    example:
        insert_include_header('path_to_file/file.cpp', '#include <iostream>')
        insert_include_header('path_to_file/file.h', '#include <iostream>')
    '''
    
    
    fe = FileEditClass()  
    return fe.insert_include_header(filename, include_statement, preview=True)

def file_edit_insert_code_block(filename: Annotated[str, "the file to insert the code block"],
                                start_line: Annotated[int, "the start line number to insert the code block (1-indexed)"],
                                code_block: Annotated[Union[str, List[str]], "the code block to insert"])->str:
    '''
    file edit: Function to insert a code block in a file
    params:
        filename: the file to insert the code block
        start_line: the start line number to insert the code block (1-indexed)
        code_block: the code block to insert

    returns:
        success: if the code block was successfully inserted
    '''         
    
    fe = FileEditClass()
    return fe.insert_code_block(filename, start_line, code_block, preview=True)

def file_edit_delete_one_line(filename: Annotated[str, "the file to delete the lines from"], 
                    line_number: Annotated[int, "the line number to delete (1-indexed)"])->str:
    '''
    Function to delete a line from a cpp/h  file
    params:
        filename: the file to delete the lines from
        line_number: the line number to delete (1-indexed)

    returns:
        success: if the line was successfully deleted
        
    example:
        delete_one_line('path_to_file/file.cpp', 10)
    '''    
    
    fe = FileEditClass()
    return fe.delete_one_line(filename, line_number, preview=True)

def file_edit_delete_code_block(filename: Annotated[str, "the file to delete the lines from"], 
                    start_line: Annotated[int, "the start line number to delete (1-indexed)"],
                    end_line: Annotated[int, "the end line number to delete (1-indexed)"])->str:
    '''
    file edit: Function to delete a code block from a cpp/h file
    params:
        filename: the file to delete the lines from
        start_line: the start line number to delete (1-indexed)
        end_line: the end line number to delete (1-indexed)

    returns:
        success: if the code block was successfully deleted

    example:
        delete_code_block('path_to_file/file.cpp', 64, 69)
    '''    
    
    fe = FileEditClass()
    return fe.delete_code_block(filename, start_line, end_line, preview=True)

def file_edit_replace_code_block(filename: Annotated[str, "the file to edit "], 
                start_line: Annotated[int, "the start line number to delete (1-indexed)"],
                end_line: Annotated[int, "the end line number to delete (1-indexed)"],
                new_code_block: Annotated[Union[str, List[str]], "the new code block to replace the old one"])->str:
    '''
    file edit: Function to replace a code block in a cpp/h file
    params:
        filename: the file to edit
        start_line: the start line number to delete (1-indexed)
        end_line: the end line number to delete (1-indexed)
        new_code_block: the new code block to replace the old one

    returns:
        success: if the code block was successfully replaced    

    example:
        replace_code_block('path_to_file/file.cpp', 64, 69, """
            Position& operator=(const Position<T>& rhs) 
                {
                    int a = 0;
                    int b = 0;
                    if (&rhs == this) return *this;
                    else { x=rhs.x; y=rhs.y; return *this; }
                }"""
        )
        replace_code_block('file.cpp', 64, 69, ['Position& operator=(const Position<T>& rhs)', '{', '    int a = 0;', '    int b = 0;', '    if (&rhs == this) return *this;', '    else { x=rhs.x; y=rhs.y; return *this; }', '}'])
    '''
    fe = FileEditClass()
    return fe.replace_code_block(filename, start_line, end_line, new_code_block, preview=True)


def file_edit_update_function_defination(filename: Annotated[str, "the cpp/h file to update the cpp function"],
                    function_name: Annotated[str, "the cpp function name to update"],
                    new_code_block: Annotated[Union[str, List[str]], "the new code block to replace the old one"])->str:
    '''
    file edit: Function to update a function in a cpp/h file
    params:
        filename: the file to update the function
        function_name: the function name to update
        new_code_block: the new code block to replace the old one

    returns:
        success: if the function was successfully updated  

        
    example 1:
        update_function_defination('path_to_file/file.cpp', 'Position& operator=(const Position<T>& rhs)', """
            Position& operator=(const Position<T>& rhs) 
                {
                    int a = 0;
                    int b = 0;
                    if (&rhs == this) return *this;
                    else { x=rhs.x; y=rhs.y; return *this; }
                }"""
        )    
    '''    
    
    fe = FileEditClass()
    return fe.update_function_defination(filename, function_name, new_code_block,preview=True)

def file_edit_rollback(filename: Annotated[str, "the file to save"]) -> str:
    '''回退一步（取消上一次编辑）'''
    fe = FileEditClass()
    fe.rollback(filename)
    return f'{filename}, roll back success, 请重新编辑'

def file_edit_save(filename: Annotated[str, "the file to save"]) -> str:
    '''所有编辑动作都已完成，提交保存'''
    fe = FileEditClass()
    files, res_file = fe.preview_to_commit(filename)
    ast = AST()
    ast.update_symbol_table(files)
    if len(res_file) == 0:
        return f'{filename} save success 所有操作均已保存'
    else:
        return f'{filename} save success. \n尚有' + ' '.join(res_file) + ' 尚未保存\n请调用"tools.function.file_edit_save"函数, 保存该文件的编辑操作\n请EDIT_REVIEW'
    

def function_dependency_query(function: Annotated[str, "PhotonArray::addTo"],
                            src_file: Annotated[str, "/home/wnk/code/GalSim/src/PhotonArray.cpp"],
                            project_path: Annotated[str, "/home/wnk/code/GalSim/"],
                            src_path: Annotated[str, "/home/wnk/code/GalSim/src"],
                            namespace: Annotated[str, "galsim"])->dict:                            
    '''
    function_dependency_query函数用于查询函数的依赖关系，包括主任务和子任务

    Args:
        function (Annotated[str, "PhotonArray::addTo"]): 函数名
        src_file (Annotated[str, "/home/wnk/code/GalSim/src/PhotonArray.cpp"]): function所在文件。绝对路径
        project_path (Annotated[str, "/home/wnk/code/GalSim/"]): 项目路径: 绝对路径
        src_path (Annotated[str, "/home/wnk/code/GalSim/src"]): 源码路径: 绝对路径
        namespace (Annotated[str, "galsim"]): 命名空间

    Returns:
        dict: 返回查询结果

    '''

    yml = '''
compilation_database_dir: {build_path}
output_directory: {build_path}
diagrams:
  {diag_name}:
    type: sequence
    glob:
      - {file}
    include:
      namespaces:
        - {namespace}
      paths:
        - {path}/src/
        - {path}/include/
    from:
      - function: "{func}"
'''

   
    path = project_path
    build_path = os.path.join(path, "build")

    # src = '/home/wnk/code/GalSim/src'  # Change this to the path of your source code directory
    # include = ['/home/wnk/code/GalSim/include/galsim/']  # Change this to the path of your include directory
    # namespaces=['galsim']
    # cache_file = 'workspace/symbol_table.pkl'

    ast = AST()
    # ast.create_cache(src, include, namespaces, cache_file, load = True)   
  
    pattern = re.compile(r'^(?P<namespace>[\w:]+)::(?P<classname>[\w:<>]+)::(?P<functionname>operator\(\)|[\w:<>~!@#$%^&*+=|]+)\(.*\)( const)?$')
    pattern2 = re.compile(r'(?P<namespace>[a-zA-Z_][\w:]*)::(?P<classname>[a-zA-Z_]\w*(?:<[^<>]*>)?)::(?P<functionname>[a-zA-Z_]\w*)\([^)]*\)')

    func_depend = {}
    func_depend['sub_task'] = {}
    func_depend['main_task'] = {}

    func = function
    file = src_file
    diag_name = 'sequence_diagram' + str(hash(function))
    yml_file = yml.format(path = path, build_path = build_path, file=file, func=func, namespace = namespace, diag_name = diag_name)
    # print(yml_file)
    with open(os.path.join(build_path, "config.yml"), "w") as f:
        f.write(yml_file)
    cmd = f"cd {build_path}; clang-uml -c config.yml -g 1"
    # os.remove(os.path.join(build_path, "sequence_diagram.json"))
    ret = subprocess.run(cmd, shell=True, capture_output=True, text=True)   
    json_file = os.path.join(build_path, diag_name + ".json")
    if not os.path.exists(json_file):
        return ret.stdout + "\n请检查输入的函数名与文件名是否正确"

    # print(json_file)
    with open(json_file, "r") as f:
        sequence_diagram = json.load(f)
    if 'participants' not in sequence_diagram:
        return ret.stdout + "clang-uml生成的sequence_diagram.json文件中没有participants字段, 请检查输入的函数名与文件名是否正确"
    participants = sequence_diagram['participants']
    if not participants:
        return ret.stdout + "clang-uml生成的sequence_diagram.json文件中participants字段为空, 请检查输入的函数名与文件名是否正确"
    for j,  participant in enumerate(participants):            
        if j == 0:            
            full_name = participant['full_name']
            func_depend['main_task'][full_name] = []
            if 'activities' not in participant:
                continue
            for activity in participant['activities']:
                func_depend['main_task'][full_name].append(activity['full_name'])
        else:            
            full_name = participant['full_name']
            func_depend['sub_task'][full_name] = []
            if 'activities' not in participant:
                continue
            activities = participant['activities'] 
            for _,  activity in enumerate(activities):
                func_depend['sub_task'][full_name].append(activity['full_name'])

    codes = set()
    for _, functions in func_depend['main_task'].items():
        for function in functions:
            match = pattern.match(function)
            if not match:
                match = pattern2.match(function)
            if match:
                namespace = match.group('namespace')
                classname = match.group('classname')
                if '<' in classname:
                    classname = classname.split('<')[0]
                functionname = match.group('functionname')
                try:
                    codes.add(ast.find_definition(functionname, classname))
                except Exception as e:
                    codes.add(f"error {functionname} {classname} {e}")
                    continue
            else:
                codes.add(f"error")
    for _, functions in func_depend['sub_task'].items():
        for function in functions:
            match = pattern.match(function)
            if not match:
                match = pattern2.match(function)
            if match:
                namespace = match.group('namespace')
                classname = match.group('classname')
                if '<' in classname:
                    classname = classname.split('<')[0]
                functionname = match.group('functionname')
                try:
                    codes.add(ast.find_definition(functionname, classname))
                except Exception as e:
                    codes.add(f"error {functionname} {classname} {e}")
                    continue  
            else:
                print('[error]', function) 

        result = dict()
        result[func] = dict()
        result[func][f'Code on which the function depends of {func}'] = sequence_diagram
        result[func][f'{func} Function dependency'] = list(codes)        

    return result
    
 