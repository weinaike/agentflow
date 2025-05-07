import re
import numpy as np
import os
from typing_extensions import Annotated, List, Union
import difflib
from clang.cindex import Cursor, CursorKind
try:
    from .utils import thread_safe_singleton
    from .abstract_syntax_tree import AST, CursorUtils, TuSymbolTable
except:
    import sys
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))    
    from utils import thread_safe_singleton
    from abstract_syntax_tree import AST, CursorUtils, TuSymbolTable
    sys.path.pop()

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

    def __init__(self):
        self.ast = AST()
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

    def _extract_symbol_table_from_code_block(self, code_block, path="tmp.cpp", virtual_files=[]):
        virtual_files.append((path, code_block))
        cb_tu = self.ast.parse_virtual_file(self.ast.index, path, virtual_files)
        symtable = TuSymbolTable(cb_tu)
        return symtable

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
                                code_block: Annotated[str, "the code block to insert"],
                                preview: bool = False, force_build=True)->str:
        try:
            master_symtable = self.ast.tu_symbol_tables.get(filename, None)    
            tu_status = self.ast.tu_status.get(filename, False)
            if master_symtable is None:
                tu_status, master_symtable = self.ast.build_tu_symbol_table(filename, None)

            context: Cursor = master_symtable.find_context(start_line) 
            if (not context.is_definition()) and context.kind in [CursorKind.CONSTRUCTOR, CursorKind.CXX_METHOD, CursorKind.FUNCTION_DECL]:
                start_line = context.extent.start.line 
                context: Cursor = master_symtable.find_context(start_line)
            context_scope = CursorUtils.get_scope(context)

            extra_symtable = self._extract_symbol_table_from_code_block(code_block)
            extra_nodes = sorted(extra_symtable.local_cursors, key=lambda cursor: cursor.extent.end.line, reverse=True)
            next_line = None

            with open(filename) as f:
                master_code = f.readlines()
            code_block = code_block.splitlines(keepends=True) if isinstance(code_block, str) else code_block

            for extra_node in extra_nodes:
                if next_line is None:
                    next_line = extra_node.extent.start.line
                elif next_line < extra_node.extent.start.line:
                    continue    
                if context_scope == CursorUtils.get_scope(extra_node):
                    next_line = extra_node.extent.end.line
                    continue
                else:
                    i, j = extra_node.extent.start.line, extra_node.extent.end.line
                    for line_no in range(j, i-1, -1):
                        master_code.insert(start_line - 1, code_block[line_no -1])

            with open(filename, "w") as f:
                f.writelines(master_code)

        except Exception as e:
            return str(e)

        if force_build:
            self.ast.build_symbol_tables()    

        return "success"            

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
                            include_statement: Annotated[str, "include statement to insert"], 
                            preview: bool = False, force_build: bool = True)->str:
        
        try:
            #filename = os.path.join(self.ast.directory, filename) #TODO:
            if not os.path.exists(filename):
                raise FileNotFoundError(f'File {filename} not found')
            tu = self.ast.parse_source_file(self.ast.index, filename)
            first_cursor = None
            for node in tu.cursor.get_children():
                if node.location.file.name == filename:
                    first_cursor = node
                    break
            assert first_cursor

            content = []
            with open(filename) as f:
                content = f.readlines()
            include_statement = include_statement + "\n" if include_statement.endswith("\n") else include_statement + "\n\n"

            line_no = first_cursor.extent.start.line    
            content.insert(line_no - 1, include_statement)

            with open(filename, "w") as f:
                f.writelines(content)

            if force_build:
                self.ast.update_symbol_tables()    
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
                    preview : bool = False,
                    force_build: bool = False)->str:
        try:
            with open(filename) as f:
                source_code = f.readlines()

            master_symtable = self.ast.tu_symbol_tables.get(filename, None)    
            if master_symtable is None:
                _, master_symtable = self.ast.build_tu_symbol_table(filename, None)
            replaced_cursor, replaced_cursor_indent = None, 0   
            for cursor in master_symtable.local_cursors:
                if cursor.extent.start.line == start_line and cursor.extent.end.line == end_line:
                    replaced_cursor = cursor
                    replaced_line = source_code[replaced_cursor.extent.start.line-1]
                    replaced_cursor_indent = len(replaced_line) - len(replaced_line.lstrip())
                    break
        
            #先只考虑是一个函数/方法的情况
            assert CursorUtils.is_callable(replaced_cursor)

            if isinstance(new_code_block, str):
                new_code_block_lines = new_code_block.splitlines(True)
                if len(new_code_block_lines) != end_line - start_line + 1:
                    empty_lines = end_line - start_line + 1 - len(new_code_block_lines)
                    for _ in range(empty_lines):
                        new_code_block_lines.extend(["\n"])
            else:
                new_code_block_lines = list(map(ensure_line, new_code_block))
                new_code_block = "".join(new_code_block_lines)    
            extra_symtable = self._extract_symbol_table_from_code_block(new_code_block)
            extra_nodes = sorted(extra_symtable.local_cursors, key=lambda cursor: cursor.extent.end.line, reverse=True)
            if len(extra_nodes) == 0:
                extra_nodes = [extra_symtable.tu.cursor]
            lines = []
            for extra_node in extra_nodes:
                start, end = extra_node.extent.start.line, extra_node.extent.end.line
                if extra_node.kind == CursorKind.NAMESPACE:
                    #TODO:
                    start += 1 if new_code_block_lines[start-1].strip().endswith("{") else 2
                    end -= 1
                assert start <= end    
                lines.extend(range(start, end+1))
            lines = np.unique(np.sort(lines))   
            refined_new_code_block = [new_code_block_lines[i-1] for i in lines]
            refined_indent = len(refined_new_code_block[0]) - len(refined_new_code_block[0].lstrip())
            gap = refined_indent - replaced_cursor_indent
            for i in range(len(refined_new_code_block)):
                if gap > 0:
                    refined_new_code_block[i] = refined_new_code_block[i][gap:]
                else:
                    refined_new_code_block[i] = " " * gap + refined_new_code_block[i]    

            source_code = source_code[:start_line-1] + refined_new_code_block + source_code[end_line:]    

            extra_start = extra_nodes[0].extent.start.line
            include_stats = [stat.lstrip() for stat in new_code_block_lines[:extra_start] if stat.strip().startswith("#include")]
            if include_stats:
                #把包含的头文件加进来：
                first_cursor = master_symtable.local_cursors[0]    
                start = first_cursor.extent.start.line
                source_code = source_code[:start-1] + include_stats + source_code[start-1:]

            with open(filename, "w") as f:
                f.writelines(source_code)    

            if force_build:
                self.ast.update_symbol_tables()    

        except Exception as e:
            print(e)
            raise e
            #return str(e)
        
        return "success"    

            


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
        dir = os.path.dirname(filename)
        if not os.path.exists(dir):
            os.makedirs(dir, exist_ok=True)
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                if isinstance(code_block, str):
                    file.write(code_block)
                else:
                    for line in code_block:
                        file.write(line + '\n')
        except Exception as e:
            print(e)
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

if __name__ == '__main__':
    # discard modifications:
    import subprocess
    #command = "cd /home/jiangbo/GalSim && git clean -dxf include src && git checkout -- src/ && git checkout -- include"
    #result = subprocess.run(command, shell=True, capture_output=True, text=True)
    #print(result.returncode)
    #print(result.stdout)
    #print(result.stderr)

    configs = [ 
        {
            "src": "/home/wnk/code/GalSim/src",
            "include": ["/home/wnk/code/GalSim/include", "/home/wnk/code/GalSim/include/galsim", "/home/wnk/code/GalSim/src", "/home/wnk/code/GalSim/downloaded_eigen/eigen-3.4.0"],
            #"scope": "galsim::SBSpergel::SBSpergelImpl",
            "scope": "galsim::SBVonKarman::SBVonKarmanImpl",
            "method": "shoot",
            "namespaces": [],
            "cache_dir": "/home/jiangbo/AutoCoder/cached_ast_dir/galsim",
            "use_cache": False,
            "output_filters": [
                lambda cursor: not cursor.location.file.name.startswith("/home/jiangbo/GalSim"),
                lambda cursor: not CursorUtils.get_namespace(cursor) == "galsim"
            ]
        }
        ,{
            "src": "/home/jiangbo/arctic/arctic/src",
            "include": ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"],

            "scope": "",
            "method": "add_cti",

            #"scope": "",
            #"method": "clock_charge_in_one_direction",

            #"scope": "TrapManagerInstantCapture",
            #"method": "n_electrons_released",

            "namespaces": [],
            "cache_dir": "/home/jiangbo/AutoCoder/cached_ast_dir/arctic",
            "use_cache": False,
            "output_filters": [
                lambda cursor: not cursor.location.file.name.startswith("/home/jiangbo/arctic/arctic")
            ]
        }
    ]

    config = configs[-2]

    src = config["src"]
    include = config["include"]
    namespaces = config["namespaces"]
    cache_dir = config["cache_dir"]
    use_cache = config["use_cache"]
    output_filters = config["output_filters"]
    method = config["method"]
    scope = config["scope"]

    ast = AST()
    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_dir, load=use_cache)
    editor = FileEditClass()

    def TESTCASE_insert_code_block_00():
        code_block = \
    '''
    #include <string>

    using namespace std;
    namespace galsim {
        void Table2D::show(const string& msg) {
        }
    }
    '''
        editor.insert_code_block("/home/wnk/code/GalSim/src/Table.cpp", 1228, code_block)

    def TESTCASE_insert_code_block_01():
        code_block = \
    '''
    #include <string>

    using namespace std;
    namespace galsim {
        void Table2D::show(const string& msg) {
        }
    }
    '''
        code_block = \
    '''
        void PhotonArray_convolve_cuda(double* d_x, double* d_y, double* d_flux);
    '''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/CuPhotonArray.h", 27, code_block)

    def TESTCASE_insert_code_block_02():
        code_block = \
    '''
        void PhotonArray_convolve_cuda(double* d_x, double* d_y, double* d_flux)
        {

        }
    '''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/CuPhotonArray.cu", 66, code_block)

    def TESTCASE_insert_code_block_03():
        code_block = \
    '''
        namespace galsim {
        void PhotonArray_convolve_cuda2(double* d_x, double* d_y, double* d_flux)
        {

        }
        }
    '''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/CuPhotonArray.cu", 66, code_block)

    def TESTCASE_insert_code_block_04():
        code_block = \
    '''
        namespace galsim {
        void PhotonArray_convolve_cuda3(double* d_x, double* d_y, double* d_flux)
        {

        }
        }
    '''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/CuPhotonArray.cu", 53, code_block)

    def TESTCASE_insert_code_block_05():
        code_block = \
'''
namespace galsim {
__global__ void addArrays(double* a, const double* b, int N); 
__global__ void multiplyArrays(double* a, const double* b, double scale, int N); 
__global__ void convolveShuffleKernel(double* d_x, double* d_y, double* d_flux,
                                      const double* d_rhs_x, const double* d_rhs_y, const double* d_rhs_flux,
                                      int N, long seed);
}
'''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/PhotonArray_convolve.cu", 5, code_block)

    def TESTCASE_insert_code_block_06():
        code_block = \
'''
namespace galsim {
__global__ void addArrays(double* a, const double* b, int N); 
__global__ void multiplyArrays(double* a, const double* b, double scale, int N); 
__global__ void convolveShuffleKernel(double* d_x, double* d_y, double* d_flux,
                                      const double* d_rhs_x, const double* d_rhs_y, const double* d_rhs_flux,
                                      int N, long seed);
}
'''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/PhotonArray_convolve.cu", 10, code_block)

    def TESTCASE_insert_code_block_07():
        code_block = \
'''
    int x = 0, y = 0;
    blockSize *= 2;
    pow(x, y);
    x = mypow(y);
'''
        editor.insert_code_block("/home/wnk/code/GalSim/src/cuda_kernels/PhotonArray_convolve.cu", 19, code_block)

    def TESTCASE_insert_include_header_01():
        editor.insert_include_header("/home/wnk/code/GalSim/include/galsim/Table.h", "#include <iostream>\n")

    def TESTCASE_replace_code_block_01():
        code_block = \
'''
    #include "myfile.h"
    namespace galsim {
        void SBExponential::SBExponentialImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        {
            //new implementation
            int x, y;
            return 0;
        }
    }
'''            
        editor.replace_code_block("/home/wnk/code/GalSim/src/SBExponential.cpp", 563, 629, new_code_block=code_block) 
    #TESTCASE_insert_include_header_01()
    #TESTCASE_insert_code_block_01()
    #TESTCASE_insert_code_block_02()
    #TESTCASE_insert_code_block_03()
    #TESTCASE_insert_code_block_04()
    #TESTCASE_insert_code_block_07()
    
    TESTCASE_replace_code_block_01()
