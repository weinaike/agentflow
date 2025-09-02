
from typing_extensions import Annotated
from typing import List, Union, Dict

from AgentFlow.tools.project_base import ProjectBase
from AgentFlow.tools.cpp_project import CppProject
from AgentFlow.tools.project import Project

_project: ProjectBase = None

def parse_project(language: Annotated[str, "Specifies the programming language of the project"], 
                  **kwargs: Annotated[Dict[str, Union[str, bool, List[str]]], "Accepts a dictionary of key-value pairs with multiple value types for Project parsing configuration"]
    ):
    global _project
    if language.upper() in ["C++", "CPP"]:
        _project = CppProject(**kwargs)
    elif language.upper() in ["PYTHON", "C", "FORTRAN"]:
        _project = Project(**kwargs)  # 类似code-graph-rag中的GraphUpdater的解析功能 
    
    return _project.__hash__()


def find_definition(symbol: Annotated[str, "name of a class, method, function, etc."],
                    type: Annotated[str, ""]=None) -> str:
    global _project
    return _project.find_definition(symbol, type)    

def fetch_source_code(symbol: Annotated[str, "name of a class, method, function, etc."],
                    type: Annotated[str, "Used for overloaded methods, functions, partially specialized classes, etc. The default is None"]=None) -> str:
    '''
    Fetches the source code of the given symbol (including its implementation and called functions). 
    @Returns code organized by files, with irrelevant lines marked as '... lines xxx-yyy omitted for brevity'.
    '''                
    global _project
    return _project.fetch_source_code(symbol, type)    

def reparse_project():
    '''
    Reparses the project: only updated source files in the project are parsed.
    '''
    global _project
    try:
        _project.parse()
    except Exception as e:
        return f"reparse project failed: {e}"    
    return "reparse project successfully"    

def close_project():
    global _project
    del _project

if __name__ == '__main__':
    language = "c++"
    config = {
        "build_options": ["-I/home/jiangbo/GalSim/include", "-I/home/jiangbo/GalSim/include/galsim", "-std=c++14", "-DENABLE_CUDA", "-I/usr/lib/gcc/x86_64-linux-gnu/12/include"], 
        "force_build": True,
        "build_dir": "/home/jiangbo/agentflow/tmp/build",
        "src_dirs": ["/home/jiangbo/GalSim/src"]
    }

    method = "galsim::Nearest::shoot"
    clazz = "galsim::Nearest"
    

    parse_project(language=language, **config)

    print(fetch_source_code(symbol=method))

    print("====")

    print(find_definition(symbol=clazz))
    
    
        