
import os
import subprocess
from typing_extensions import Annotated, List, Union
try:
    from .utils import calculate_degrees
    from .file_edit import FileEditClass
    from .abstract_syntax_tree import AST
except ImportError:
    from utils import calculate_degrees
    from file_edit import FileEditClass
    from abstract_syntax_tree import AST
import re
import json
import logging

logger = logging.getLogger(__name__)
   
def find_definition(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                    class_name:Annotated[str, "The class name to which the function or variable belongs."] = None) -> dict:
    """
    该方法已过时，请使用fetch_source_code方法。
    以下示例演示了如何查找函数或变量的定义。
        如果要查询galsim名字空间内的PhotonArray类的addTo的定义，symbol为'addTo', class_name为'galsim::PhotonArray'，即调用：
            find_definition("addTo", "galsim::PhotonArray")
        如果addTo只是在galsim名字空间内定义的，那么调用：
            find_definition("addTo", "galsim")    
        如果addTo是定义的一个全局函数，那么调用：
            find_definition("addTo", "")    
        如果要查询galsim名字空间内的UniformDeviate类的声明，symbol为'', classs_name为'galsim::UniformDeviate'，即调用：
            find_declaration("", "galsim::UniformDeviate")    
    """
    ast = AST()
    return ast.find_definition(symbol, class_name)

def find_declaration(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                     class_name:Annotated[str, "The class name to which the function or variable belongs."] = None)-> dict:
    '''
    该方法已过时，请使用fetch_source_code方法。
    以下示例演示了如何查找函数或变量的声明（如果查询声明未找到结果，可直接查询定义替代）。
        如果要查询galsim名字空间内的PhotonArray类的addTo的声明，symbol为'addTo', class_name为'galsim::PhotonArray'，即调用：
            find_declaration("addTo", "galsim::PhotonArray")
        如果addTo只是在galsim名字空间内声明的，那么调用：
            find_declaration("addTo", "galsim")    
        如果addTo是声明的一个全局函数，那么调用：
            find_declaration("addTo", "")    
        如果要查询galsim名字空间内的UniformDeviate类的声明，symbol为'', classs_name为'galsim::UniformDeviate'，即调用：
            find_declaration("", "galsim::UniformDeviate")    
    '''
    ast = AST()
    return ast.find_declaration(symbol, class_name)

def fetch_source_code(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                     class_name:Annotated[str, "The class name to which the function or variable belongs."] = None)-> dict:
    '''
    查询函数及其调用的相关代码。该方法相对于find_declaration/find_definition的优点是可以一次查询到全部相关的代码，减少查询次数。建议使用该方法查询代码。
    该方法用法示例如下：
        若需要查询函数Bounds及其调用函数的相关代码, 符号为'Bounds'：
            fetch_source_code("Bounds")
        若需要查询galsim::SBVonKarman::SBVonKarmanImpl::shoot方法及其调用的相关代码，符号为'shoot', class_name为'galsim::SBVonKarman::SBVonKarmanImpl'
            fetch_source_code("shoot", "galsim::SBVonKarman::SBVonKarmanImpl')    
    '''
    
    ast = AST()

    dir_list = [ast.directory]
    dir_list.extend(ast.include)
  
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]


    return ast.fetch_source_code(symbol, class_name, filters=output_filters)

def fetch_source_code_snippet(symbol:Annotated[str, "The name of the function or variable that needs to be queried."],
                     class_name:Annotated[str, "The class name to which the function or variable belongs."] = None)-> dict:
    '''
    通过C++代码的抽象语法树，查询函数及其调用的相关代码。不会主动包含头文件。
    例如：
        若需要查询函数Bounds及其调用函数的相关代码, 符号为'Bounds'：
            fetch_source_code("Bounds")
        若需要查询galsim::SBVonKarman::SBVonKarmanImpl::shoot方法及其调用的相关代码，符号为'shoot', class_name为'galsim::SBVonKarman::SBVonKarmanImpl'
            fetch_source_code("shoot", "galsim::SBVonKarman::SBVonKarmanImpl')    
    '''
    
    ast = AST()

    dir_list = [ast.directory]
    dir_list.extend(ast.include)
  
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]


    return ast.fetch_source_code(symbol, class_name, filters=output_filters, with_header=False)

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



def query_right_name(names:Annotated[List[str], "The names of the functions that needs to be queried."])-> dict:
    '''
    基于C++代码的抽象语法树，对列表中的函数名(可能不准确)进行查询， 获取准确的函数名。
    例如： 
        输入： names = ["SBInterpolatedKImage::shoot",
                        "SBAiry::shoot",
                        "SBExponential::shoot",
                        "SBSersic::shoot"
                        ]
        返回：
            right_names = query_right_name(names)
            print(right_names)
            {
                "SBInterpolatedKImage::shoot": "SBInterpolatedKImage::shoot",
                "SBAiry::shoot": "SBAiry::shoot",
                "SBExponential::shoot": "SBExponential::SBExponentialimpl::shoot",
                "SBSersic::shoot": "SBSersic::SBSersicimpl::shoot"
            }
    '''
    ast = AST()

    name_map = {}

    for name in names:
        function_name = name
        class_name = None
        if '::' in name:
            items = name.split('::')
            function_name = items[-1]
            class_name =  items[-2]
        try:
            content = ast.find_definition(symbol = function_name, class_name = None)
        except Exception as e:
            name_map[name] = f"{name}并不存在"
            continue
        functions = content[function_name]
        if len(functions) == 0:
            name_map[name] = f"{name}并不存在"
        else:
            for function in functions:
                if class_name in function["symbol"]:
                    if name in name_map:
                        name_map[name].append(function["symbol"])
                    name_map[name] = [function["symbol"]]
                    
                    
    return name_map


def query_important_functions(functions:Annotated[List[str], "The names of the functions that needs to be queried."])-> List[str]:
    '''
    该函数将分析输入函数的所有依赖函数，将这些依赖绘制为调用图，分析调用图中的关键节点，即：被多个函数调用的中间函数或者基础函数， 形成重要函数列表
    例如：
        输入： functions = [
                    "galsim::PhotonArray::addTo",
                    "galsim::PhotonArray::convolve",
                    "galsim::SBProfile::shoot",
                    "galsim::SBVonKarman::SBVonKarmanImpl::shoot",
                    "galsim::SBConvolve::SBConvolveImpl::shoot",
                    "galsim::SBAutoConvolve::SBAutoConvolveImpl::shoot",
                    ]
        返回：
            important_functions = query_important_functions(functions)
            print(important_functions)
            [
                "galsim::OneDimensionalDeviate::shoot",
                "galsim::UniformDeviate::UniformDeviate",
                "galsim::PhotonArray::size",
                "galsim::PhotonArray::getTotalFlux",
                "galsim::OneDimensionalDeviate::OneDimensionalDeviate",
            ]
    '''

    ast = AST()

    dir_list = [ast.directory]
    dir_list.extend(ast.include)
  
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]

    callgraphs = []
    for function in functions:
        method = function.split("::")[-1]
        scope = "::".join(function.split("::")[:-1])
        try:
            callgraph = ast.get_call_graph(method, scope, filters=output_filters)
        except Exception as e:
            logger.error(f"获取{function}的调用图失败, {e}")
            continue
        callgraphs.append(callgraph)

    merge_callgraph = {}
    for callgraph in callgraphs:
        merge_callgraph.update(callgraph.to_dict())
    degree = calculate_degrees(merge_callgraph)
    degree = dict(sorted(degree.items(), key=lambda x:  (x[1][0] + 1) * (x[1][1] - 1) , reverse=True))

    important_functions = []
    topK = 10
    for i, key in enumerate(degree.keys()):
        important_functions.append(key)
        if i == topK:
            break
    return important_functions


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


def file_edit_update_function_definition(filename: Annotated[str, "the cpp/h file to update the cpp function"],
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
        update_function_definition('path_to_file/file.cpp', 'Position& operator=(const Position<T>& rhs)', """
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
    return fe.update_function_definition(filename, function_name, new_code_block,preview=True)

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
    ast.update_symbol_tables()
    if len(res_file) == 0:
        return f'{filename} save success 所有操作均已保存'
    else:
        return f'{filename} save success. \n尚有' + ' '.join(res_file) + ' 尚未保存\n请调用"tools.function.file_edit_save"函数, 保存该文件的编辑操作\n请EDIT_REVIEW'
    
def file_edit_save_to_file(filename: Annotated[str, "the file to save"],
        content: Annotated[str, "content to be written"]
    ) -> str: 
    '''将指定的内容写入文件中。若文件不存在，则创建该文件；若文件已经存在，则原文件内容会被清除'''
    try:
        with open(filename, 'w') as f:
            if isinstance(content, str):
                f.write(content)
            elif isinstance(content, list):
                for line in content:
                    f.write(line)    
    except Exception as e:
        return f'save file `{filename}` failed: {e}'
    return f'save file `{filename}` success'                    

def file_edit_rollback_files(filenames: Annotated[List[str], "files to be restored"])->str:
    '''将指定列表filenames中的文件回滚或删除，使git仓库恢复到修改前的状态'''
    fe = FileEditClass()
    return fe.file_edit_rollback_files(filenames)


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
        return ret.stdout + "\n请检查输入的函数名(function)与文件名(src_file)是否正确"

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
    
 
