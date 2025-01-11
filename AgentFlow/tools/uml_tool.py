
from typing_extensions import Annotated
from .file_tool import parse_yml_content
import os
import subprocess
import re
import shutil

def generate_uml(project_path:Annotated[str, "../path/to/project"], yml_file_content:Annotated[str,""]) ->str:
    """
    generate_uml函数生成UML类图中包含以下步骤:
    1. 运行CMake配置项目: cmake project_path -DCMAKE_EXPORT_COMPILE_COMMANDS=ON; build目录为workspace/build
    2. 生成clang-uml配置文件: 将yml_file_content内容存为 workspace/build/clang-uml-config.yml
    3. 运行clang-uml生成UML类图: clang-uml clang-uml-config.yml, 生成的UML类图存放在workspace/build/class_diagram.puml文件中
    4. 读取workspace/build/class_diagram.puml文件, 返回UML类图内容

    Args:
        project_path (str): 项目路径
        yml_file_content (str): clang-uml的配置文件内容
    Returns:
        str: UML类图

    example:
        uml_content = generate_uml("/home/wnk/code/galsim/", yml_file_content)
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
    

    subprocess.run(['rm', 'CMakeCache.txt'], cwd=build_path, text=True, capture_output=True)  
    cmake_result = subprocess.run(['cmake', project_path, '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], cwd=build_path, text=True, capture_output=True)
    if cmake_result.returncode != 0:
        return cmake_result.stderr
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
        with open(puml_path, 'r') as f:
            uml_content = f.read()
        if not uml_content:
            return f"{puml_path}中生成UML类图内容为空，请检查配置文件"
    except FileNotFoundError:
        return "f{puml_path} file not found"
    content = f"clang-uml的配置文件：{conf_path}, \n生成UML类图成功，存于{puml_path}\nUML类图部分内容如下，详细内容查看源文件：\n{uml_content[:500]}\n"
    return content



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
    with open(puml_file_name+'_new.puml', 'w') as file:
        file.writelines(new_lines)

    with open(puml_file_name+'_new.puml', 'r') as file:
        content = file.read()
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
        uml_content = generate_python_uml("/home/wnk/code/galsim/", "/home/wnk/code/workspace/backup")
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
    



