import os
import subprocess
from typing_extensions import Annotated
from typing import Union, List
import shutil

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
        ret = get_derived_class_of_class("SBProfile", "/home/jiangbo/GalSim/include/galsim/")

        ret = """
    /home/jiangbo/GalSim/include/galsim/SBMoffatImpl.h:    class SBMoffat::SBMoffatImpl : public SBProfileImpl
    /home/jiangbo/GalSim/include/galsim/SBInclinedExponentialImpl.h:    class SBInclinedExponential::SBInclinedExponentialImpl : public SBProfileImpl
    /home/jiangbo/GalSim/include/galsim/SBTransformImpl.h:    class SBTransform::SBTransformImpl : public SBProfileImpl
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
    print(get_cpp_dir_structure('/home/jiangbo/GalSim/'))