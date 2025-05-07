from typing_extensions import Annotated
import re


def read_file_content(file_path:Annotated[str, "The path to the file"])->str:
    """读取yaml, json, txt等文本文件内容"""
    with open(file_path, 'r') as f:
        content = f.read()

    # 内容长度控制
    if len(content) > 51200:
        content = content[:51200] + '...\n内容过长，已截断显示'

    return content



## 从文本中提取代码块
def extract_code_blocks(content, language='yaml'):   
    """Regular expression to match code blocks"""

    code_block_pattern = re.compile(rf'```{language}(.*?)```', re.DOTALL)
    code_blocks = code_block_pattern.findall(content)

    # list -> str
    code_blocks = '\n'.join(code_blocks)
    
    return code_blocks


