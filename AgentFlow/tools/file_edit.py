import re
import os
from typing_extensions import Annotated, List, Union
import difflib
import subprocess
try:
    from .utils import thread_safe_singleton
except ImportError:
    from utils import thread_safe_singleton

preview_promt = '''
-----------------------------------------------------
本次编辑结果如上，请找出其中的缺陷
1. 如果存在缺陷, 调用'tools.function.file_edit_rollback'函数，放弃本次编辑。并指出缺陷的内容
2. 如果无缺陷, 请调用'tools.function.file_edit_save'函数, 保存本次编辑
请 EDIT_REVIEW
-----------------------------------------------------
'''

def ensure_line(s):
    if not s.endswith('\n'):
        s += '\n'
    return s
@thread_safe_singleton
class FileEditClass:

    def __init__(self, ):
        self.preview_function_list = {
            'insert_code_block': self.insert_code_block, 
            'insert_include_header': self.insert_include_header,
            'delete_one_line': self.delete_one_line, 
            'delete_code_block': self.delete_code_block, 
            'replace_code_block': self.replace_code_block,
            'update_function_definition': self.update_function_definition,
            }
        self.preview_func = dict()
        for func in self.preview_function_list.keys():
            self.preview_func[func] = []
        self.n = 10
    roll_back_description = '''
回退一步（取消上一次编辑）
'''
    def rollback(self, filename: Annotated[str, "the file to rollback"]):
        for func, params in self.preview_func.items():
            for param in params:
                if param['filename'] == filename:
                    self.preview_func[func].remove(param)

    save_description = '''
所有编辑动作都已完成，提交保存
'''
    def save(self, filename: Annotated[str, "the file to save"]):
        self.preview_to_commit(filename)

    def preview_to_commit(self, filename: Annotated[str, "the file to save"]):
        file_name = []
        res_file = []
        for func, params in self.preview_func.items():
            for param in params:
                if param['filename'] == filename:
                    self.preview_function_list[func](**param)
                    if filename not in file_name:
                        file_name.append(param['filename'])
                    self.preview_func[func].remove(param)   
                else:
                    if param['filename'] not in res_file:
                        res_file.append(param['filename']) 
        return file_name, res_file

    insert_code_block_description = '''
file edit: Function to insert a code block in a file
params:
    filename: the file to insert the code block
    start_line: the start line number to insert the code block (1-indexed)
    code_block: the code block to insert

returns:
    success: if the code block was successfully inserted
'''

    def insert_code_block(self, filename: Annotated[str, "the file to insert the code block"],
                                start_line: Annotated[int, "the start line number to insert the code block (1-indexed)"],
                                code_block: Annotated[Union[str, List[str]], "the code block to insert"],
                                preview: bool = False)->str:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            if preview:
                # Create a diff of the code block to be inserted
                self.preview_func['insert_code_block'].append( {'filename':filename, 'start_line':start_line, 'code_block':code_block})
                if isinstance(code_block, str):
                    code_block = code_block.splitlines(keepends=True)
                    code_block += '\n'
                else:
                    for i in range(len(code_block)):
                        code_block[i] = ensure_line(code_block[i])
                    code_block += '\n'
                diff = difflib.unified_diff(lines, lines[:start_line-1] + code_block + lines[start_line-1:], n = self.n)
                return filename+'\n' + ''.join(diff) + preview_promt


            with open(filename, 'w', encoding='utf-8') as file:
                for i, line in enumerate(lines):
                    if i+1 == start_line:
                        if isinstance(code_block, str):
                            file.write(code_block + '\n')
                        else:
                            for new_line in code_block:
                                # new_line 如果没有\n结尾, 则增加\n
                                new_line = ensure_line(new_line)
                                file.write(new_line)
                            file.write('\n')
                    file.write(line)
        except Exception as e:
            return str(e)
        return 'success'


    insert_include_header_description = '''
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
    def insert_include_header(self, filename:Annotated[str, "the file to insert the include statement"],
                            include_statement: Annotated[str, "include statement to insert"], preview: bool = False)->str:
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f'File {filename} not found')
        
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        try:
            # Detect if it's a .h or .cpp file
            is_header = filename.endswith(('.h', '.hpp', '.hxx', '.hh', '.cuh'))

            # Define regex patterns
            include_pattern = re.compile(r'^\s*#include\s+[<"].+[>"]')
            pragma_once_pattern = re.compile(r'^\s*#pragma\s+once')
            ifndef_pattern = re.compile(r'^\s*#ifndef\s+\w+')
            define_pattern = re.compile(r'^\s*#define\s+\w+')
            single_line_comment_pattern = re.compile(r'^\s*//')
            multi_line_comment_start_pattern = re.compile(r'^\s*/\*')
            multi_line_comment_end_pattern = re.compile(r'.*\*/\s*$')

            # Process lines to find where to insert the include statement
            new_lines = []
            inserted = False
            in_multi_line_comment = False

            if is_header:
                pragma_once_found = False
                ifndef_found = False
                define_found = False

                for line in lines:
                    if pragma_once_pattern.match(line):
                        pragma_once_found = True
                    elif ifndef_pattern.match(line):
                        ifndef_found = True
                    elif define_pattern.match(line) and ifndef_found:
                        define_found = True
                        new_lines.append(line)
                        new_lines.append(include_statement + '\n')
                        inserted = True
                        continue

                    new_lines.append(line)

                if not inserted:
                    if pragma_once_found or (ifndef_found and define_found):
                        pass  # Already handled by previous logic
                    else:
                        new_lines.insert(0, include_statement + '\n')
            else:
                include_section_ended = False
                has_include = False
                for line in lines:
                    # Handle multi-line comments
                    if in_multi_line_comment:
                        new_lines.append(line)
                        if multi_line_comment_end_pattern.search(line):
                            in_multi_line_comment = False
                        continue

                    if multi_line_comment_start_pattern.match(line):
                        in_multi_line_comment = True
                        new_lines.append(line)
                        continue

                    # Handle single-line comments
                    if not has_include:
                        if single_line_comment_pattern.match(line):
                            new_lines.append(line)
                            continue

                    if include_pattern.match(line):
                        new_lines.append(line)
                        has_include = True
                    elif not include_section_ended and line.strip() :
                        include_section_ended = True
                        new_lines.append(include_statement + '\n')
                        new_lines.append(line)
                        inserted = True
                    else:
                        new_lines.append(line)

                if not inserted:
                    new_lines.append(include_statement + '\n')

            if preview:
                self.preview_func['insert_include_header'].append( {'filename':filename, 'include_statement':include_statement})
                diff = difflib.unified_diff(lines, new_lines, n = self.n)
                return filename+'\n' + ''.join(diff) + preview_promt

            with open(filename, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)
        except Exception as e:
            return str(e)
        return 'success'


    delete_one_line_description = '''
Function to delete a line from a cpp/h  file
params:
    filename: the file to delete the lines from
    line_number: the line number to delete (1-indexed)

returns:
    success: if the line was successfully deleted
    
example:
    delete_one_line('path_to_file/file.cpp', 10)
'''

    def delete_one_line(self, filename: Annotated[str, "the file to delete the lines from"], 
                    line_number: Annotated[int, "the line number to delete (1-indexed)"], 
                    preview:bool = False)->str:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if preview:
                self.preview_func['delete_one_line'].append({'filename':filename, 'line_number':line_number})
                diff = difflib.unified_diff(lines, lines[:line_number-1] + lines[line_number:], n = self.n)
                return  filename+'\n' +''.join(diff) + preview_promt
            
            with open(filename, 'w', encoding='utf-8') as file:
                for i, line in enumerate(lines):
                    if i+1 != line_number:
                        file.write(line)
        except Exception as e:
            return str(e)
        return 'success'

    delete_code_block_description = '''
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
    def delete_code_block(self, filename: Annotated[str, "the file to delete the lines from"], 
                    start_line: Annotated[int, "the start line number to delete (1-indexed)"],
                    end_line: Annotated[int, "the end line number to delete (1-indexed)"],
                    preview:bool = False)->str:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if preview:
                self.preview_func['delete_code_block'].append({'filename':filename, 'start_line':start_line, 'end_line':end_line})
                diff = difflib.unified_diff(lines, lines[:start_line-1] + lines[end_line:], n = self.n)
                return filename+'\n' +''.join(diff) + preview_promt

            
            with open(filename, 'w', encoding='utf-8') as file:
                for i, line in enumerate(lines):
                    if i+1 < start_line or i+1 > end_line:
                        file.write(line)
        except Exception as e:
            return str(e)
        return 'success'

    replace_code_block_description = '''
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
    def replace_code_block(self, filename: Annotated[str, "the file to edit "], 
                    start_line: Annotated[int, "the start line number to delete (1-indexed)"],
                    end_line: Annotated[int, "the end line number to delete (1-indexed)"],
                    new_code_block: Annotated[Union[str, List[str]], "the new code block to replace the old one"], 
                    preview : bool = False)->str:
        try:
            # If the new code block is a string, split it into lines
            if isinstance(new_code_block, str):
                new_code_block = (new_code_block + '\n').splitlines(keepends=True) 
            else:
                for i in range(len(new_code_block)):
                    new_code_block[i] = ensure_line(new_code_block[i])
            
            with open(filename, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Determine the indentation level of the start line
            indent_level = 0
            if start_line <= len(lines):
                indent_level = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
            
            # Create the indented new code block
            indented_new_code_block = [' ' * indent_level + new_line for new_line in new_code_block]


            if preview:
                self.preview_func['replace_code_block'].append({'filename':filename, 'start_line':start_line, 'end_line':end_line, 'new_code_block': new_code_block})
                diff = difflib.unified_diff(lines, lines[:start_line-1] + indented_new_code_block + lines[end_line:], n = self.n)
                return filename+'\n' +''.join(diff) + preview_promt

            
            with open(filename, 'w', encoding='utf-8') as file:
                for i, line in enumerate(lines):
                    if i+1 < start_line or i+1 > end_line:
                        file.write(line)
                    elif i+1 == start_line:
                        for new_line in indented_new_code_block:
                            file.write(new_line)
                    else:
                        pass
        except Exception as e:
            return str(e)
        return 'success'



    find_function_range_description = '''
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
    def find_function_range(self, filename: Annotated[str, "the file to locate the function"],
                            function_name: Annotated[str, "the function name to locate"])->tuple[int, int]:
        with open(filename, 'r') as file:
            lines = file.readlines()

        function_pattern = re.compile(rf'{re.escape(function_name)}')
        brace_pattern = re.compile(rf"{re.escape('{')}")
        end_pattern = re.compile(rf"{re.escape('}')}")
        comment_pattern = re.compile(r'//.*|/\*.*\*/')

        start = None
        end = None
        brace_count = None
        for i, line in enumerate(lines):
            line = comment_pattern.sub('', line)  # remove comments
            if start is None and function_pattern.search(line):
                # 找到函数名后，还需要向前找到函数的开始，即向前找空行，注释或者}等确认是本函数的开始
                for j in range(i, -1, -1):
                    pre_line = lines[j].strip()
                    pre_line_no_comment = comment_pattern.sub('', pre_line).strip()
                    if pre_line == '' or pre_line.startswith('//') or pre_line.startswith('/*') or pre_line.endswith('*/') \
                        or pre_line_no_comment.endswith(';') or pre_line_no_comment.endswith('}') :
                        start = j + 1
                        break
                    
            
            if start is not None:
                # print(brace_count)
                if brace_pattern.search(line) :
                    if brace_count is None:
                        brace_count = 1
                    else:
                        brace_count += line.count('{')
                if end_pattern.search(line):
                    brace_count -= line.count('}')
                if brace_count == 0:
                    end = i
                    break
        if start == None or end == None:
            return None, None
        return start + 1, end + 1 # 1-indexed


    update_function_definition_description = '''
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

    def update_function_definition(self, filename: Annotated[str, "the cpp/h file to update the cpp function"],
                        function_name: Annotated[str, "the cpp function name to update"],
                        new_code_block: Annotated[Union[str, List[str]], "the new code block to replace the old one"],
                        preview : bool = False)->str:
        start, end = self.find_function_range(filename, function_name)

        if start is None or end is None:
            return f'Function {function_name} not found in file {filename}'

        ret = self.replace_code_block(filename, start, end, new_code_block, preview)
        if preview :
            self.preview_func['update_function_definition'].append({'filename':filename, 'function_name':function_name, 'new_code_block': new_code_block})
            return ret    
        if ret != 'success':
            return ret
        return 'success'



    save_code_to_file_description = '''
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
    def save_code_to_new_file(self, filename: Annotated[str, "the file to save the code to"],
                        code_block: Annotated[Union[str, List[str]], "the code block to save"])->str:
        if os.path.exists(filename):
            return f'File {filename} already exists, please edit file instead. eg: insert/delete the code block or update the function '
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                if isinstance(code_block, str):
                    file.write(code_block)
                else:
                    for line in code_block:
                        file.write(line + '\n')
        except Exception as e:
            return str(e)    
        return 'success'


    read_code_from_file_description = '''
Function to read code from a file
params:
    filename: the file to read the code from

returns:
    str: the content of the file
    exception: if an exception occurred while reading the file
'''
    def read_code_from_file(self, filename: str)->str:
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                content_lines = file.readlines()
        except Exception as e:
            return str(e)
        
        # Determine the width for line numbers based on the total number of lines
        line_number_width = len(str(len(content_lines)))
        
        content = ""
        for index, line in enumerate(content_lines, start=1):
            # Format line number with fixed width
            line_number = f"{index}".rjust(line_number_width)
            content += f"{line_number}: {line}"
    
        return content

    read_function_from_file_description = '''
Function to read a function from a file
params:
    filename: the file to read the function from
    function_name: the function name to read

returns:
    str: the content of the function
    exception: if an exception occurred while reading the file

'''
    def read_function_from_file(self, filename: str, function_name: str)->str:
        start, end = self.find_function_range(filename, function_name)
        if start is None or end is None:
            return f'Function {function_name} not found in file {filename}'
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Determine the width for line numbers based on the total number of lines
        line_number_width = len(str(end))
        
        content_with_line_numbers = ""
        for index, line in enumerate(lines[start-1:end], start=start):
            # Format line number with fixed width
            line_number = f"{index}".rjust(line_number_width)
            content_with_line_numbers += f"{line_number}: {line}"

        return content_with_line_numbers

    def file_edit_rollback_files(self, filenames):
        rollback_log = ""
        for filename in filenames:
            #判断git是否跟踪文件
            if not os.path.exists(filename):
                rollback_log += f"rollback file `{filename}` error: file not found\n"
                continue
            if not os.path.isfile(filename):
                rollback_log += f"rollback file `${filename}` error: not a regular file\n"
            dir, base = os.path.dirname(filename), os.path.basename(filename)
            ls_cmd = f'cd {dir} && git ls-files --error-unmatch {base}'
            result = subprocess.run(ls_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                #文件被跟踪
                rollback_cmd = f'cd {dir} && git checkout -- {base}'
                result = subprocess.run(rollback_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    rollback_log += f"rollback file `{filename}` successfully\n"
                else:
                    rollback_log += f"rollback file `{filename}` failed: {result.stderr}\n"    
            else:
                #文件未被跟踪
                rm_cmd = f'cd {dir} && git status && test -f {base} && test -w {base} && rm -f {base}'        
                result = subprocess.run(rm_cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    rollback_log += f"delete file `{filename}` successfully\n"
                else:
                    rollback_log += f"delete file `{filename}` failed: {result.stderr}\n"    

        return rollback_log        
                
if __name__ == '__main__':
    fe = FileEditClass()
    
    # print(fe.insert_include_header('file.cpp', "#include \"<iostream>\"", preview= True))
    # print(fe.delete_one_line('file.cpp', 2, preview=True))
#     print(fe.delete_code_block('file.cpp', 1, 3, preview=True))
    print(fe.replace_code_block('file.cpp', 1, 3, new_code_block="void Nearest::shoot(PhotonArray& photons, UniformDeviate ud) const {\n#ifdef ENABLE_CUDA\n    Nearest_shoot_cuda(photons, ud);\n#else\n    const int N = photons.size();\n    dbg<<\"Nearest shoot: N = \"<<N<<std::endl;\n    dbg<<\"Target flux = 1.\\n\";\n    double fluxPerPhoton = 1./N;\n    for (int i=0; i<N; i++)  {\n        photons.setPhoton(i, ud()-0.5, ud()-0.5, fluxPerPhoton);\n    }\n    dbg<<\"Nearest Realized flux = \"<<photons.getTotalFlux()<<std::endl;\n#endif\n}", preview=True))
#     print(fe.replace_code_block('file.cpp', 1, 3, ['Position& operator=(const Position<T>& rhs)', '{', '    int a = 0;', '    int b = 0;', '    if (&rhs == this) return *this;', '    else { x=rhs.x; y=rhs.y; return *this; }', '}'], preview=True))
    # print(fe.find_function_range('file.cpp', 'Position& operator=(const Position<T>& rhs)'))
    # print(fe.update_function_definition('file.cpp','fluxRadius', ['Position& operator=(const Position<T>& rhs)\n', '{\n', '    int a = 0;\n', '    int b = 0;\n', '    if (&rhs == this) return *this;\n', '    else { x=rhs.x; y=rhs.y; return *this; }\n', '}\n'], preview=True))
    # print(fe.save_code_to_new_file('file.cpp', ['Position& operator=(const Position<T>& rhs)', '{', '    int a = 0;', '    int b = 0;', '    if (&rhs == this) return *this;', '    else { x=rhs.x; y=rhs.y; return *this; }', '}']))
    # print(fe.insert_code_block('file.cpp', 3, '#include <iostream>\n#include <iostream>\n#include <iostream>\n#include <iostream>\n', preview= True))