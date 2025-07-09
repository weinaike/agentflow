
from typing_extensions import Annotated, List
import yaml
import os
import subprocess
import re
import shutil


def parse_yml_content(yml_file_content):
    """解析 YAML 内容
    :param yml_file_content: YAML 文件内容
    :return: compilation_database_dir, path
    """

    config : dict = yaml.safe_load(yml_file_content)
    
    # 提取 output_directory
    compilation_database_dir = config.get('compilation_database_dir')
    output_directory = config.get('output_directory')
        
    # 提取 class_diagram 配置
    diagram_names = list(config.get('diagrams', {}).keys())
    path = os.path.join(output_directory, diagram_names[0] + '.puml')

    return compilation_database_dir, path


def read_plantuml_file(puml_file_name:Annotated[str, "The path to the PlantUML file"]) -> str:
    """读取PlantUML文件内容，并将其中的类标签替换为类名"""


    with open(puml_file_name, 'r') as file:
        lines = file.readlines()

    # 定义正则表达式模式
    pattern = re.compile(r'(enum|class|abstract)\s+"[^"]+"\s+as\s+\w+')

    # 处理每一行，过滤掉匹配的行
    new_lines = [line for line in lines if not pattern.match(line) or '<' in line]

    filter = [line for line in lines if pattern.match(line) and '<' not in line]

    class_label = dict()
    for line in filter:
        # class "FrameData" as C_0013329636936515615170
        # 通过正则表达式，提取 FrameData 和 C_0013329636936515615170
        match = re.search(r'(enum|class|abstract)\s+"([^"]+)"\s+as\s+\w+', line)
        if match:
            class_name = match.group(2)
        else:
            print('not match')
        label = re.search(r'as\s+(\w+)', line).group(1)   
        class_label[label] = class_name

    # 将标签替换为类名
    # class C_0013329636936515615170 替换为 class "FrameData"
    for i, line in enumerate(new_lines):
        for label, class_name in class_label.items():
            new_lines[i] = new_lines[i].replace(label, f'{class_name}')

    # 将处理后的内容写回文件
    with open(puml_file_name, 'w') as file:
        file.writelines(new_lines)

    content = ''.join(new_lines)
    return content



def generate_cpp_uml(project_path:Annotated[str, "../path/to/project"], yml_file_content:Annotated[str,""], build_method:Annotated[str,"cmake or make"]) ->str:
    """
    generate_cpp_uml函数生成UML类图中包含以下步骤:
    1. 运行CMake配置项目: cmake project_path -DCMAKE_EXPORT_COMPILE_COMMANDS=ON; build目录为workspace/build
    2. 生成clang-uml配置文件: 将yml_file_content内容存为 workspace/build/clang-uml-config.yml
    3. 运行clang-uml生成UML类图: clang-uml clang-uml-config.yml, 生成的UML类图存放在workspace/build/class_diagram.puml文件中
    4. 读取workspace/build/class_diagram.puml文件, 返回UML类图内容


    Args:
        project_path (str): 项目路径
        yml_file_content (str): clang-uml的配置文件内容
        build_method (str): 编译方法，cmake 或 make            
            # 对于cmake编译方法，clang-uml-config.yml 中字段compilation_database_dir一般为CMakeList.txt下一级的build目录下
            # 对于mkae构建模式，clang-uml-config.yml 中字段compilation_database_dir一般与makefile同级

    Returns:
        str: UML类图

    example:
        uml_content = generate_cpp_uml("/home/jiangbo/project/", yml_file_content)


    yml_file_content 配置文件内容示例:
    ```yaml
    # compilation_database_dir 编译路径使用绝对路径,即compile_commands.json所在路径
    # 对于cmake编译方法，CMakeList.txt下一级的build目录下， 对于mkae构建模式，一般与makefile同级
    compilation_database_dir: /home/jiangbo/project/build
    # output_directory 类图输出使用绝对路径
    output_directory: /home/jiangbo/project/build/diagrams
    diagrams:
    # 类图名称， 根据需要调整
    main_class_diagram:
        # 类图类型，固定为class
        type: class
        glob:
        # 一个路径仅能够包含一个*通配符
        # glob字段可多行, 需保证包含所有.cpp源文件，不需要包含.h头文件与.cu核函数文件; 
        - /home/jiangbo/project/src/*.cpp
        - /home/jiangbo/project/src/math/*.cpp
        # 使用命名空间，有助于提升类图的可读性
        include:
        namespaces:
            - xxx
        # exclude 排除类图命名空间范围，例如std, boost可以简化类图
        exclude:
        namespaces:
            - std
            - xxx
        # 使用命名空间，有助于提升类图的可读性
        using_namespace:
        - xxx
    ```

    """

    build_path, puml_path = parse_yml_content(yml_file_content)
    if not os.path.isabs(build_path):
        build_path = os.path.join(project_path, build_path)

    if not os.path.exists(build_path):
        os.makedirs(build_path)
        if not os.path.exists(build_path):
            return f"compilation_database_dir 配置不正确，且 build目录{build_path}创建失败， 请修改compilation_database_dir配置内容, 采用已存在或可一次创建的绝对路径"
    if not os.path.isabs(puml_path):
        puml_path = os.path.join(project_path, puml_path)
    uml_dir = os.path.dirname(puml_path)
    if not os.path.exists(uml_dir) :
        os.makedirs(uml_dir)
        if not os.path.exists(uml_dir):
            return f"output_directory 配置不正确，且 UML目录{uml_dir}创建失败， 请修改output_directory配置内容， 采用已存在或可一次创建的绝对路径"  
    
    if build_method == "cmake":
        subprocess.run(['rm', 'CMakeCache.txt'], cwd=build_path, text=True, capture_output=True)  
        cmake_result = subprocess.run(['cmake', project_path, '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], cwd=build_path, text=True, capture_output=True)
        if cmake_result.returncode != 0:
            return cmake_result.stderr + '\n请确认项目的构建方法是否为make, 并提供准确的compilation_database_dir'
    elif build_method == "make":
        make_result = subprocess.run(['make', 'clean'], cwd=build_path, text=True, capture_output=True)
        make_result = subprocess.run(['bear','--', 'make'], cwd=build_path, text=True, capture_output=True)
        if make_result.returncode != 0:
            return make_result.stderr + '\n请确认项目的构建方法是否为cmake, 并提供准确的compilation_database_dir'
    # print(cmake_result.stderr, cmake_result.stdout)
    # make
    # make_result = subprocess.run(['make', '-j12'], cwd="workspace/build", text=True, capture_output=True)
    # if make_result.returncode != 0:
    #     return make_result.stderr

    # Write the YAML configuration file for clang-uml
    conf_path = os.path.join(build_path, "clang_uml_config.yml")
    with open(conf_path, 'w') as config_file:
        config_file.write(yml_file_content)
    # Run clang-uml to generate UML diagrams
    uml_result = subprocess.run(['clang-uml', '-c', 'clang_uml_config.yml'], cwd=build_path, text=True, capture_output=True)
    if '[error] ' in uml_result.stdout:
        return uml_result.stdout + "\n配置出错，请检查\nglob: 配置的路径应该是绝对路径, 同时仅需源文件，无需.h头文件 与.cu核函数文件 "
    ## 解析 yml_file_content， 提取 output_directory 以及 class_diagram 的配置
    try:        
        uml_content = read_plantuml_file(puml_path)
        if not uml_content:
            return f"{puml_path}中生成UML类图内容为空，请检查配置文件"
    except FileNotFoundError:
        return f"run generate_cpp_uml fail. output {puml_path} file not found"
    content = f"clang-uml的配置文件：{conf_path}, \n生成UML类图成功，存于{puml_path}\nUML类图部分内容如下，详细内容查看源文件：\n{uml_content[:500]}\n"
    return content

def generate_python_uml(project_path:Annotated[str, "../path/to/project"], backup_dir:Annotated[str, "../path/to/backup_dir"]) ->str:
    """
    generate_python_uml函数生成python代码库的UML类图中包含以下步骤:
    1. 运pyreverse -A  -o puml /path/to/project, 生成classes.puml文件与packages.puml文件
    2. 生成的文件备份至backup_dir目录下
    4. 读取备份目录下的classes.puml文件 与 packages.puml 返回UML类图内容

    Args:
        project_path (str): 项目路径
        backup_dir (str): 文档备份目录
    Returns:
        str: UML类图

    example:
        uml_content = generate_python_uml("/home/jiangbo/project/", "/home/jiangbo/workspace/backup")
    """

    pyreverse = subprocess.run(['pyreverse','-A', '-o', 'puml', f'{project_path}'], cwd='.', text=True, capture_output=True)
    print(pyreverse)
    if pyreverse.returncode != 0:
        return pyreverse.stderr

    # 备份生成的文件，将classes.puml文件与packages.puml文件备份至backup_dir目录下
    backup_dir = os.path.abspath(backup_dir)
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir, exist_ok=True)
    try:
        # 拷贝classes.puml文件到backup_dir目录下
        classes_backup = os.path.join(backup_dir, 'classes.puml')
        shutil.move('classes.puml', classes_backup)

        # 拷贝packages.puml文件到backup_dir目录下
        packages_backup = os.path.join(backup_dir, 'packages.puml')
        shutil.move('packages.puml', packages_backup)

        # 读取备份目录下的classes.puml文件与packages.puml文件内容
        with open(classes_backup, 'r') as f:
            classes_content = f.read()

        content = f"生成UML类图存于{classes_backup}\n详细内容如下：\n{classes_content}\n"

        try:
            with open(packages_backup, 'r') as f:
                packages_content = f.read()

            content += f"生成UML类图存于{packages_backup}\n详细内容如下：\n{packages_content}\n"
        except FileNotFoundError:
            pass
        return content
    except Exception as e:
        return f"备份文件失败，{e}"
    

def extract_classes(text: str):
    # 正则表达式匹配类信息
    pattern = re.compile(r'class "(.*?)" as (.*?)\nclass \2 \{\n(.*?)\n\}', re.DOTALL)
    pattern2 = re.compile(r'abstract "(.*?)" as (.*?)\nabstract \2 \{\n(.*?)\n\}', re.DOTALL)
    matches = pattern.findall(text)
    matches.extend(pattern2.findall(text))
    
    id_map = {}
    class_info = {}
    for match in matches:
        class_info[match[0]] = f'{{\n{match[2]}\n}}'
        id_map[match[1]] = match[0]
    return class_info, id_map

def extract_connect(text: str) -> list:
    # 正则表达式匹配所有类型的关系符号
    relation_pattern = re.compile(r'(C_\d+)\s+([-.o*+<>|]{3,4})\s+(C_\d+)\s*(:\s*.*)?')
    relation_matches = relation_pattern.findall(text)
    
    connections = []
    for match in relation_matches:
        connection = {
            'source': match[0],
            'relation': match[1],
            'target': match[2],
            'label': match[3].strip() if match[3] else ''
        }
        connections.append(connection)
    return connections


def extract_class_names_from_uml(puml_file_name:Annotated[str, "UML类图文件"]) -> list[str]:
    """
    extract_class_names_from_uml函数提取UML类图中的类名

    Args:
        puml_file_name (str): UML类图文件
    Returns:
        list: 类名列表

    example:
        class_names = extract_class_names_from_uml(uml_content)
    """
    with open(puml_file_name, 'r') as file:
        content = file.read()
    class_info, _ = extract_classes(content)
    
    # 提取类名    
    return class_info.keys()


def extract_connect_from_uml(puml_file_name:Annotated[str, "UML类图文件"]) -> str:
    """
    extract_connect_from_uml函数提取UML类图中的类之间的关系

    Args:
        puml_file_name (str): UML类图文件
    Returns:
        str: 类之间的关系

    example:
        connect = extract_connect_from_uml(puml_file_name)
    """

    with open(puml_file_name, 'r') as file:
        content = file.read()

    connections = extract_connect(content)

    _, ip_map = extract_classes(content)

    # 提取类之间的关系
    for conn in connections:
        if conn['source'] in ip_map:
            conn['source'] = ip_map[conn['source']]
        if conn['target'] in ip_map:
            conn['target'] = ip_map[conn['target']]        

    # 拼接输出字符串
    connect = '@startuml'
    for conn in connections:
        connect += f"{conn['source']} {conn['relation']} {conn['target']} {conn['label']}\n"
    connect += '@enduml'
    return connect

def extract_class_structure_from_uml(puml_file_name:Annotated[str, "UML类图文件"], class_name : Annotated[str, "类名"]) -> str:
    """
    extract_class_structure_from_uml函数提取UML类图中的类结构

    Args:
        puml_file_name (str): UML类图文件
    Returns:
        str: 类结构

    example:
        class_structure = extract_class_structure_from_uml(puml_file_name)
    """
    with open(puml_file_name, 'r') as file:
        content = file.read()

    class_info, _ = extract_classes(content)

    # 提取类结构
    class_structure = ''
    for key, val in class_info.items():
        if class_name in key:
            class_structure += f"class {key} {val}\n"
    return class_structure


def extract_Inheritance_classes_from_uml(puml_file_name:Annotated[str, "UML类图文件"], class_name:Annotated[str, "类名"]) -> list[str]:
    """
    extract_Inheritance_classes_from_uml 函数从UML类图中提取与输入类存在继承或派生关系的类

    Args:
        class_name (str): 类名
        puml_file_name (str): UML类图文件
    Returns:
        list: 继承关系类名列表

    example:
        inheritance_classes = extract_Inheritance_classes_from_uml("class_name", puml_file_name)
    """
    with open(puml_file_name, 'r') as file:
        content = file.read()
    connections = extract_connect(content)
    _, ip_map = extract_classes(content)

    for conn in connections:
        if conn['source'] in ip_map:
            conn['source'] = ip_map[conn['source']]
        if conn['target'] in ip_map:
            conn['target'] = ip_map[conn['target']]        
    
    inheritance_classes = []
    for conn in connections:
        if '<|--' != conn['relation']:
            continue
        if (class_name in conn['source'] or class_name in conn['target']) :
            inheritance_classes.append(conn)

    outputs = []
    for conn in inheritance_classes:
        outputs.append(f'{conn["source"]} {conn["relation"]} {conn["target"]}')

    return outputs




def extract_inter_class_relationship_from_uml(puml_file_name:Annotated[str, "UML类图文件"],  
                                              class_list:Annotated[List[str], "类名列表"]) -> str:
    """
    extract_inter_class_relationship_from_uml 函数提取UML类图中的给定类之间的关系

    Args:
        puml_file_name (str): UML类图文件
        class_list (List[str]): 类名列表
    Returns:
        str: 类之间的关系

    example:
        connect = extract_inter_class_relationship_from_uml(puml_file_name)
    """

    with open(puml_file_name, 'r') as file:
        content = file.read()

    connections = extract_connect(content)

    _, ip_map = extract_classes(content)

    # 提取类之间的关系
    for conn in connections:
        if conn['source'] in ip_map:
            conn['source'] = ip_map[conn['source']]
        if conn['target'] in ip_map:
            conn['target'] = ip_map[conn['target']]        

    # 拼接输出字符串
    connect = '@startuml'
    for conn in connections:
        left = False
        right = False
        for class_name in class_list:
            if '::' in class_name:
                class_name = class_name.split('::')[-1]
            if class_name in conn['source'] :
                left = True
                break
        for class_name in class_list:
            if '::' in class_name:
                class_name = class_name.split('::')[-1]
            if class_name in conn['target'] :
                right = True
                break
        if left and right:
            connect += f"{conn['source']} {conn['relation']} {conn['target']} {conn['label']}\n"
    connect += '@enduml'
    return connect


if __name__ == '__main__':
    file = '/home/wnk/code/GalSim/build/docs/diagrams/main_class.puml'
    content = extract_class_names_from_uml(file)
    # print(content)
    content = extract_connect_from_uml(file)
    # print(content)
    content = extract_Inheritance_classes_from_uml(file, 'SBProfile')
    print(content)
