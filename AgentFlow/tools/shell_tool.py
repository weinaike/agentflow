import os
import subprocess
import shutil
from pathlib import Path
from typing import Union, List, Dict, Any, Annotated
import asyncio
import logging
import json

try:
    from .utils import thread_safe_singleton
except ImportError:
    from utils import thread_safe_singleton

logger = logging.getLogger(__name__)

@thread_safe_singleton
class CommandExecutor:
    """命令执行器"""
    
    def __init__(self, working_dir: str = "/workspace"):
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir = self.working_dir
        
    async def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行shell命令"""
        try:
            # 先分割命令
            commands = self._split_compound_command(command)
            
            all_stdout = []
            all_stderr = []
            final_return_code = 0
            
            # 逐个执行命令
            for cmd in commands:
                cmd = cmd.strip()
                if not cmd:
                    continue
                    
                if cmd.startswith('cd '):
                    # 处理cd命令
                    result = await self._handle_cd_command(cmd)
                    if result['stderr']:
                        all_stderr.append(result['stderr'])
                    if result['return_code'] != 0:
                        final_return_code = result['return_code']
                        # cd失败时，通常应该停止执行后续命令
                        break
                else:
                    # 执行其他命令
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(self.current_dir)
                    )
                    
                    try:
                        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                        if stdout:
                            stdout_text = stdout.decode('utf-8', errors='replace')
                            # 如果内容过长，只保留最后10000个字符
                            if len(stdout_text) > 10000:
                                stdout_text = '内容过长，仅显示最后10000个字符\n' + stdout_text[-10000:]
                            all_stdout.append(stdout_text)
                        if stderr:
                            stderr_text = stderr.decode('utf-8', errors='replace')
                            # 如果内容过长，只保留最后30000个字符
                            if len(stderr_text) > 10000:
                                stderr_text = '内容过长，仅显示最后10000个字符\n' + stderr_text[-10000:]
                            all_stderr.append(stderr_text)
                        if process.returncode != 0:
                            final_return_code = process.returncode
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                        all_stderr.append(f"Command '{cmd}' timed out after {timeout} seconds")
                        final_return_code = -1
                        break
            
            return {
                "stdout": '\n'.join(all_stdout),
                "stderr": '\n'.join(all_stderr),
                "return_code": final_return_code,
                "working_dir": str(self.current_dir),
                "success": final_return_code == 0
            }
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "working_dir": str(self.current_dir),
                "success": False
            }
    
    async def _handle_cd_command(self, command: str) -> Dict[str, Any]:
        """处理cd命令"""
        try:
            path_part = command.strip()[3:].strip()  # 移除'cd '
            if not path_part or path_part == '~':
                new_dir = self.working_dir
            else:
                if path_part.startswith('/'):
                    new_dir = Path(path_part)
                else:
                    new_dir = self.current_dir / path_part
                new_dir = new_dir.resolve()
            
            # 检查目录是否存在
            if new_dir.exists() and new_dir.is_dir():
                self.current_dir = new_dir
                return {
                    "stdout": "",
                    "stderr": "",
                    "return_code": 0,
                    "working_dir": str(self.current_dir),
                    "success": True
                }
            else:
                return {
                    "stdout": "",
                    "stderr": f"cd: {path_part}: No such file or directory",
                    "return_code": 1,
                    "working_dir": str(self.current_dir),
                    "success": False
                }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"cd: {str(e)}",
                "return_code": 1,
                "working_dir": str(self.current_dir),
                "success": False
            }

    def _split_compound_command(self, command: str) -> List[str]:
        """分割复合命令，支持 ; && || 分隔符"""
        # 这是一个简化的实现，实际的shell解析会更复杂
        commands = []
        current_cmd = ""
        i = 0
        
        while i < len(command):
            char = command[i]
            
            if char == ';':
                commands.append(current_cmd.strip())
                current_cmd = ""
                i += 1
            elif char == '&' and i + 1 < len(command) and command[i + 1] == '&':
                commands.append(current_cmd.strip())
                current_cmd = ""
                i += 2
            elif char == '|' and i + 1 < len(command) and command[i + 1] == '|':
                commands.append(current_cmd.strip())
                current_cmd = ""
                i += 2
            else:
                current_cmd += char
                i += 1
        
        if current_cmd.strip():
            commands.append(current_cmd.strip())
        
        return commands



async def run_command(command: str, timeout: int = 300) -> Dict[str, Any]:
    """
    执行shell命令
    Args:
        command (str): 要执行的shell命令
        timeout (int): 超时时间（秒），默认300秒
    Returns:
        Dict[str, Any]: 命令执行结果的字典
    """
    logger.info(f"Executing command: {command}")
    executor = CommandExecutor()
    result = await executor.execute_command(command, timeout)
    return result


async def get_working_directory() -> str:
    """
    获取当前工作目录
    Returns:
        str: 当前工作目录路径
    """
    executor = CommandExecutor()
    return str(executor.current_dir)


async def list_directory(path: str = ".") -> Dict[str, Any]:
    """
    列出目录内容
    Args:
        path (str): 目录路径，默认为当前目录
    Returns:
        Dict[str, Any]: 目录内容的字典
    """
    executor = CommandExecutor()
    try:
        if path == ".":
            target_path = executor.current_dir
        elif path.startswith('/'):
            target_path = Path(path)
        else:
            target_path = executor.current_dir / path
            
        if not target_path.exists():
            return {"error": f"Path does not exist: {path}"}
            
        if not target_path.is_dir():
            return {"error": f"Path is not a directory: {path}"}
            
        items = []
        for item in sorted(target_path.iterdir()):
            stat = item.stat()
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "permissions": oct(stat.st_mode)[-3:]
            })
            
        return {
            "path": str(target_path),
            "items": items
        }
        
    except Exception as e:
        logger.error(f"List directory error: {e}")
        return {"error": str(e)}


async def read_file(file_path: str, start_line: int = 1, end_line: int = None, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    读取文件内容, 支持指定行范围(从1开始)；对于大文件，建议使用分页读取；
    Args:
        file_path (str): 文件路径
        start_line (int): 起始行号，默认1（包含）
        end_line (int): 结束行号，默认None（读取到文件末尾，包含）
        encoding (str): 文件编码，默认utf-8
    Returns:
        Dict[str, Any]: 文件内容或错误信息的字典
    """
    executor = CommandExecutor()
    try:
        if file_path.startswith('/'):
            target_path = Path(file_path)
        else:
            target_path = executor.current_dir / file_path
            
        if not target_path.exists():
            return {"error": f"File does not exist: {file_path}"}
            
        if not target_path.is_file():
            return {"error": f"Path is not a file: {file_path}"}
        
        # 参数验证
        if start_line < 1:
            start_line = 1
        
        if end_line is not None and end_line < start_line:
            end_line = start_line

        with open(target_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        
        # 如果起始行超出文件范围
        if start_line > total_lines:
            return {
                "file_path": str(target_path),
                "total_lines": total_lines,               
                "start_line": start_line,
                "end_line": end_line,
                "content": "",
                "actual_lines_read": 0,
                "message": f"start_line {start_line} exceeds file length {total_lines}"
            }
        
        # 确定实际的结束行
        actual_end_line = min(end_line, total_lines) if end_line is not None else total_lines
        
        # 提取指定行范围的内容（Python数组索引从0开始，所以要减1）
        selected_lines = lines[start_line-1:actual_end_line]
        content = ''.join(selected_lines)
        
        return {
            "file_path": str(target_path),
            "total_lines": total_lines,
            "start_line": start_line,
            "end_line": actual_end_line,
            "content": content,
            "actual_lines_read": len(selected_lines),
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Read file error: {e}")
        return {"error": str(e)}


async def write_file(file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    写入文件内容
    Args:
        file_path (str): 文件路径
        content (str): 文件内容
        encoding (str): 文件编码，默认utf-8
    Returns:
        Dict[str, Any]: 操作结果的字典
    """
    try:
        executor = CommandExecutor()
        if file_path.startswith('/'):
            target_path = Path(file_path)
        else:
            target_path = executor.current_dir / file_path
            
        # 创建父目录
        target_path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(target_path, 'w', encoding=encoding) as f:
            f.write(content)
            
        return {
            "file_path": str(target_path),
            "message": "File written successfully",
            "size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Write file error: {e}")
        return {"error": str(e)}


async def get_environment() -> Dict[str, Any]:
    """
    获取详细的环境信息，包括系统信息、编译工具版本、硬件信息等
    Returns:
        Dict[str, Any]: 环境信息的字典
    """
    try:
        executor = CommandExecutor()
        env_info = {
            "python_version": os.sys.version,
            "platform": os.name,
            "working_directory": str(executor.current_dir),
            "environment_variables": dict(os.environ),
            "path": os.environ.get('PATH', '').split(os.pathsep)
        }
        
        # 定义要执行的命令列表
        commands = {
            # 基础工具位置检查
            "tool_locations": "which gcc g++ make cmake git python python3 pip pip3 clang clang++ ninja autoconf automake libtool pkg-config gdb lldb valgrind 2>/dev/null || echo 'not found'",
            
            # 编译器版本信息
            "gcc_version": "gcc --version 2>/dev/null || echo 'gcc not found'",
            "gpp_version": "g++ --version 2>/dev/null || echo 'g++ not found'", 
            "clang_version": "clang --version 2>/dev/null || echo 'clang not found'",
            "clangpp_version": "clang++ --version 2>/dev/null || echo 'clang++ not found'",
            
            # 编译器标准支持检查
            "gcc_standards": "echo | gcc -dM -E -x c++ - | grep __cplusplus 2>/dev/null || echo 'gcc c++ standard check failed'",
            "gcc_supported_standards": "gcc -v --help 2>&1 | grep -E 'std=c\\+\\+' | head -5 2>/dev/null || echo 'gcc standards not available'",
            "clang_standards": "echo | clang++ -dM -E -x c++ - | grep __cplusplus 2>/dev/null || echo 'clang c++ standard check failed'",
            
            # 构建工具版本
            "cmake_version": "cmake --version 2>/dev/null || echo 'cmake not found'",
            "make_version": "make --version 2>/dev/null || echo 'make not found'",
            "ninja_version": "ninja --version 2>/dev/null || echo 'ninja not found'",
            "autoconf_version": "autoconf --version 2>/dev/null || echo 'autoconf not found'",
            "automake_version": "automake --version 2>/dev/null || echo 'automake not found'",
            "libtool_version": "libtool --version 2>/dev/null || echo 'libtool not found'",
            
            # 包管理工具
            "pkg_config_version": "pkg-config --version 2>/dev/null || echo 'pkg-config not found'",
            "pkg_config_path": "pkg-config --variable pc_path pkg-config 2>/dev/null || echo 'PKG_CONFIG_PATH not available'",
            
            # 调试工具
            "gdb_version": "gdb --version 2>/dev/null | head -1 || echo 'gdb not found'",
            "lldb_version": "lldb --version 2>/dev/null || echo 'lldb not found'",
            "valgrind_version": "valgrind --version 2>/dev/null || echo 'valgrind not found'",
            
            # 系统开发库检查
            "installed_dev_packages": "dpkg -l | grep -E '(build-essential|libc6-dev|linux-headers|libstdc)' 2>/dev/null || rpm -qa | grep -E '(gcc|glibc-devel|kernel-headers|libstdc)' 2>/dev/null || echo 'dev packages check failed'",
            
            # CUDA环境检查（如果存在）
            "nvcc_version": "nvcc --version 2>/dev/null || echo 'nvcc not found'",
            "nvidia_smi": "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader,nounits 2>/dev/null || echo 'nvidia-smi not available'",
            "cuda_paths": "ls -la /usr/local/cuda* 2>/dev/null || echo 'CUDA installation not found'",
            
            # 链接器信息
            "ld_version": "ld --version 2>/dev/null || echo 'ld not found'",
            "ld_library_path": "echo $LD_LIBRARY_PATH",
            "library_search_paths": "ldconfig -v 2>/dev/null | grep '^/' | head -10 || echo 'ldconfig failed'",
            
            # 系统信息
            "git_version": "git --version 2>/dev/null || echo 'git not found'",
            "system_info": "uname -a 2>/dev/null || echo 'uname not available'",
            "os_release": "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo 'OS release info not available'",
            "cpu_info": "lscpu | head -15 2>/dev/null || echo 'lscpu not available'",
            "memory_info": "free -h 2>/dev/null || echo 'free command not available'",
            "disk_info": "df -h 2>/dev/null || echo 'df command not available'",
            
            # 环境变量检查
            "cc_env": "echo CC=$CC",
            "cxx_env": "echo CXX=$CXX", 
            "cflags_env": "echo CFLAGS=$CFLAGS",
            "cxxflags_env": "echo CXXFLAGS=$CXXFLAGS",
            "ldflags_env": "echo LDFLAGS=$LDFLAGS",
            "cmake_prefix_path": "echo CMAKE_PREFIX_PATH=$CMAKE_PREFIX_PATH",
            
            # 常用开发库检查
            "opencv_check": "pkg-config --modversion opencv4 2>/dev/null || pkg-config --modversion opencv 2>/dev/null || echo 'OpenCV not found'",
            "boost_check": "ls /usr/include/boost/version.hpp /usr/local/include/boost/version.hpp 2>/dev/null | head -1 || echo 'Boost headers not found'",
            "eigen_check": "ls /usr/include/eigen3 /usr/local/include/eigen3 2>/dev/null | head -1 || echo 'Eigen3 not found'",
            "openmp_check": "echo '#include <omp.h>' | gcc -x c -fopenmp -E - >/dev/null 2>&1 && echo 'OpenMP available' || echo 'OpenMP not available'",
            
            # 架构和特性支持
            "cpu_features": "lscpu | grep -E '(Flags|Features)' 2>/dev/null || echo 'CPU features not available'",
            "architecture": "uname -m 2>/dev/null || echo 'architecture not available'"
        }
        
        # 并行执行所有命令
        for key, cmd in commands.items():
            try:
                result = await executor.execute_command(cmd, timeout=10)
                if result['success']:
                    env_info[key] = result['stdout'].strip()
                else:
                    env_info[key] = f"Error: {result['stderr']}"
            except Exception as e:
                env_info[key] = f"Error executing command: {str(e)}"
        
        return env_info
        
    except Exception as e:
        logger.error(f"Get environment error: {e}")
        return {"error": str(e)}


async def glob_search(pattern: str, path: str = '.') -> list:
    """
    使用glob模块在指定路径下查找匹配的文件或目录。
    Args:
        pattern (str): 匹配模式，如 '*.py'、'**/*.cpp' 等。
        path (str): 搜索的起始目录，默认为当前目录。
    Returns:
        list: 匹配到的文件或目录的绝对路径列表。
    Example:
        glob_search('*.py', '/home/user/project')
    """
    import glob
    search_path = os.path.join(path, pattern)
    # recursive=True 支持 ** 通配符
    results = glob.glob(search_path, recursive=True)
    # 返回绝对路径
    return [os.path.abspath(f) for f in results]


def run_shell_code(code:Annotated[str, "The shell code to run"], 
                   path:Annotated[str, "the directory to run the shell code"] = None) -> str:
    '''
    run_shell_code: Run the shell code in the given path

    Args:
        code (Annotated[str, "The shell code to run"]): The shell code to run

        path (Annotated[str, "the directory to run the shell code"]): The directory to run the shell code

    Returns:
        str: The output of the shell code

    Example:    
        code = """
        ls
        """
        print(run_shell_code(code))
        # Output: file1 file2 file3
        
    '''
    if path is None:
        result = subprocess.run(code, shell=True, text=True, capture_output=True)
    else:
        result = subprocess.run(code, shell=True, text=True, capture_output=True, cwd=path)

    if result.stderr:
        return result.stderr
    # 文本输出长度控制
    if len(result.stdout) > 30000:
        return '内容过长，仅显示最后10000个字符\n' + result.stdout[-30000:] 
    else:
        return result.stdout



def get_derived_class_of_function(func:Annotated[str, "function"], src_path:Annotated[str, "path to source code"])->str:
    '''
        查询函数的所有派生类实现，由于查询的时派生类是否实现，因而需要提供源码路径（绝对路径）

        Args: 
            func (str): 函数名
            src_path (str): 源码路径（绝对路径）

        Returns:
            str: 查询到的信息

        Example:
            ret = get_derived_class_of_function("shoot", "/home/jiangbo/project/src")

            ret = """
        src/SBVonKarman.cpp:    void VonKarmanInfo::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBVonKarman.cpp:    void SBVonKarman::SBVonKarmanImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBConvolve.cpp:    void SBConvolve::SBConvolveImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBConvolve.cpp:    void SBAutoConvolve::SBAutoConvolveImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        src/SBConvolve.cpp:    void SBAutoCorrelate::SBAutoCorrelateImpl::shoot(PhotonArray& photons, UniformDeviate ud) const
        """
    '''
    
    item = func.split('::')
    if len(item) == 1:
        cmd = 'grep -r "::{}" {}'.format(func, src_path)
    else:
        func = item[-1]
        cmd = 'grep -r "::{}" {}'.format(func, src_path)
    return run_shell_code(cmd)


def get_derived_class_of_class(class_name:Annotated[str, "class name"], inc_path:Annotated[str, "path to include code"])->str:
    '''
    查询类的所有派生类， 由于派生类声明代码文件通常放在头文件目录， 因而需要提供头文件目录（绝对路径）

    Args:
        class_name (str): 类名
        inc_path (str): 头文件路径（绝对路径）

    return:
        str: 查询到的信息

    Example:
        ret = get_derived_class_of_class("SBProfile", "/home/wnk/code/GalSim/include/galsim/")

        ret = """
    /home/wnk/code/GalSim/include/galsim/SBMoffatImpl.h:    class SBMoffat::SBMoffatImpl : public SBProfileImpl
    /home/wnk/code/GalSim/include/galsim/SBInclinedExponentialImpl.h:    class SBInclinedExponential::SBInclinedExponentialImpl : public SBProfileImpl
    /home/wnk/code/GalSim/include/galsim/SBTransformImpl.h:    class SBTransform::SBTransformImpl : public SBProfileImpl
    “”“
    '''    
    
    
    cmd = 'grep -r ": public {}" {}'.format(class_name, inc_path)
    return run_shell_code(cmd)


def run_cmake_and_make(path:Annotated[str, "The path to the bulid directory"])->str:  

    '''
    run_cmake_and_make: Run cmake and make in the given path to build the project

    Args:
        path (Annotated[str, "The path to the bulid directory"]): The path to the bulid directory

        the following commands will be run in the given path:
        cmake command : cmake .. -DENABLE_CUDA=ON
        make command : make -j12
        make build command : make build    

    Returns:
        str: The output of the cmake and make command

    Example:
        path = "/home/jiangbo/galsim_cuda/build"
        print(run_cmake_and_make(path))
        # Output: 
        # -- Configuring done
        # -- Generating done
        # -- Build files have been written to: /home/jiangbo/galsim_cuda/build
        # Scanning dependencies of target galsim_cuda
        # [ 50%] Building CXX object CMakeFiles/galsim_cuda.dir/galsim_cuda.cpp.o
        # [100%] Linking CXX shared library libgalsim_cuda.so
        # [100%] Built target galsim_cuda

    '''

    subprocess.run(['rm', 'CMakeCache.txt'], cwd=path, text=True, capture_output=True)  
    cmake_result = subprocess.run(['cmake', '..', '-DENABLE_CUDA=ON'], cwd=path, text=True, capture_output=True)
    if cmake_result.stderr:
        return cmake_result.stderr
    make_result = subprocess.run(['make', 'DEFINES="-DENABLE_CUDA"', '-j12'], cwd=path, text=True, capture_output=True)
    if make_result.stderr:
        return make_result.stderr
    
    return cmake_result.stdout + make_result.stdout

def run_make(path:Annotated[str, "The path to the bulid directory"])->str:    
    '''
    run_make: Run make in the given path to build the project

    Args:
        path (Annotated[str, "The path to the bulid directory"]): The path to the bulid directory

        the following commands will be run in the given path:
        make command : make
        make build command : make build

    Returns:
        str: The output of make command
    '''

    subprocess.run(['rm', 'CMakeCache.txt'], cwd=path, text=True, capture_output=True)

    cmake_result = subprocess.run(['cmake', '..', '-DENABLE_CUDA=ON'], cwd=path, text=True, capture_output=True)
    if cmake_result.stderr:
        return cmake_result.stderr    
    make_result = subprocess.run(['make', 'DEFINES="-DENABLE_CUDA"', '-j12'], cwd=path, text=True, capture_output=True)
    if make_result.stderr:
        return make_result.stderr
    make_build_result = subprocess.run(['make', 'install'], cwd=path, text=True, capture_output=True)
    if make_build_result.stderr:        
        return  make_build_result.stderr
    test_result = subprocess.run(['python', '../examples/demo0.py'], cwd=path, text=True, capture_output=True)
    if test_result.stderr:        
        return  test_result.stderr    
    
    return make_result.stdout + make_build_result.stdout + test_result.stdout




def run_python_code(code:Annotated[str, "The python code to run"], 
                    path:Annotated[str, "the directory to run the python code"] = None)->str:
    '''
    run_python_code: Run the python code in the given path

    Args:
        code (Annotated[str, "The python code to run"]): The python code to run

        path (Annotated[str, "the directory to run the python code"]): The directory to run the python code

    Returns:
        str: The output of the python code

    Example:    
        code = """
        print("Hello World")
        """
        print(run_python_code(code))
        # Output: Hello World


    '''

    if path is None:
        result = subprocess.run(['python3', '-c', code], text=True, capture_output=True)
    else:
        result = subprocess.run(['python3', '-c', code], cwd=path, text=True, capture_output=True)
    if result.stderr:
        return result.stderr
    return result.stdout



def get_cpp_dir_structure(path:Annotated[Union[str, List[str]], "The path to the directory"])->dict:
    '''
    "
    get_cpp_dir_structure: Get the directory structure of the given path. find all the .cpp, .cu, .h, .cuh, .c files

    Args:
        path (Annotated[Union[str, List[str]], '']): The path to the directory

    Returns:
        dict: The directory structure of the given path

    Example: 
        path = ['/home/jiangbo/galsim_cuda/']
        print(get_cpp_dir_structure(path))
    "
    '''
    special_files = ['makefile', 'cmakelists.txt', 'readme.md']

    dir_structure = {}
    if isinstance(path, str):
        path = [path]
    
    for p in path:           
        for root, dirs, files in os.walk(p):

            root = root.replace(p, "")
            root = root.replace("\\", "/")
            if root.startswith('build') or root.startswith('CMakeFiles') or root.startswith('cmake'):
                continue
            if root == "":
                root = p
            for file in files:
                if file.endswith((".cpp", ".cu", ".h", ".cuh", ".c")) or file.lower() in special_files:
                    if root not in dir_structure:
                        dir_structure[root] = []
                    dir_structure[root].append(file)
    return dir_structure


def get_dir_structure_with_tree_cmd(path:Annotated[ Union[str, List[str]], "The path to the directory"], 
                                    directories_only: Annotated[bool, "" ]= False) -> str:
    '''
    "
    get_dir_structure_with_tree_cmd: Get the directory structure of the given path

    Args:
        path (Annotated[Union[str, List[str]], '']): The path to the directory

    Returns:
        dict: The directory structure of the given path

    Example: 
        path = ['/home/jiangbo/galsim_cuda/']
        print(get_dir_structure_with_tree_cmd(path))
    "
    '''    
    command = ['tree']
    if directories_only:
        command.append('-d')
    if isinstance(path, list):
        command.extend(path)
    else:
        command.append(path)

    result = subprocess.run(command, text=True, capture_output=True)

    if result.stderr:
        return result.stderr
    return result.stdout


def show_dir_content(path:Annotated[ Union[str, List[str]], "The path to the directory"]) -> str:
    '''
    "
    show_dir_content: Get the directory structure of the given path

    Args:
        path (Annotated[Union[str, List[str]], '']): The path to the directory

    Returns:
        dict: The directory structure of the given path

    Example: 
        path = ['/home/wnk/code/galsim_cuda/']
        print(show_dir_content(path))
    "
    '''    
    command = ['tree']
    command.append('-L')
    command.append('1')
    if isinstance(path, list):
        command.extend(path)
    else:
        command.append(path)

    result = subprocess.run(command, text=True, capture_output=True)

    if result.stderr:
        return result.stderr + "\n请安装工具后重试"
    return result.stdout



def file_backup(source: str, backup_dir: str) -> str:
    """
    Backs up the source file to the specified backup directory.
    Returns the backup file path.
    """
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    filename = os.path.basename(source)
    destination = os.path.join(backup_dir, filename)
    shutil.copy2(source, destination)
    
    ret = f' File {source} is backed up to {destination}'

    return ret


if __name__ == '__main__':
    print(get_cpp_dir_structure('/home/wnk/code/GalSim/'))