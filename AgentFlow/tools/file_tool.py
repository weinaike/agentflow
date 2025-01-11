from typing_extensions import Annotated
import re
import yaml
import os

def read_file_content(file_path:Annotated[str, "The path to the file"])->str:
    """读取yaml, json, txt等文本文件内容"""
    with open(file_path, 'r') as f:
        content = f.read()
    return content



## 从文本中提取代码块
def extract_code_blocks(content, language='yaml'):   
    """Regular expression to match code blocks"""

    code_block_pattern = re.compile(rf'```{language}(.*?)```', re.DOTALL)
    code_blocks = code_block_pattern.findall(content)

    # list -> str
    code_blocks = '\n'.join(code_blocks)
    
    return code_blocks



def read_clang_uml_readme_file()->str:
    """调用这个函数，读取clang-uml的配置文件使用说明"""

    with open("tasks/configuration_file.md", 'r') as f:
        content = f.read()
    return content



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
