from autogen_agentchat.messages import TextMessage

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent

from autogen_core import CancellationToken
from autogen_agentchat.ui import Console

from ..data_model import get_model_config, ModelEnum        
from ..tools import AST
from .arctic_prompts import GENERATE_COMPLETE_CODE_SYSTEM_PROMPT, GENERATE_CODE_SNIPPET_SYSTEM_PROMPT, GENERATE_UNIFIED_DIFF_SYSTEM_PROMPT, MERGE_CODE_SNIPPETS_SYSTEM_PROMPT

import asyncio
import re
import subprocess
import time
from tempfile import NamedTemporaryFile

def extract_code_blocks(content, language='yaml'):   
    """Regular expression to match code blocks"""

    if isinstance(language, str):
        code_block_pattern = re.compile(rf'```{language}\n(.*?)```', re.DOTALL)
    else:
        language = "|".join(language)    
        code_block_pattern = re.compile(rf'```(?:{language})\n(.*?)```', re.DOTALL)
    code_blocks = code_block_pattern.findall(content)

    return code_blocks

class Generator:
    def __init__(self, config):
        self.config = config
        self.llm_config = get_model_config(self.config)
        self.default_system_prompt = None 

    async def __call__(self, func, system_prompt=None, loop_times=1):
        msgs = [TextMessage(content=func, source="user")]    
        model_client = OpenAIChatCompletionClient(**self.llm_config.model_dump(), max_tokens=None if self.llm_config.model.startswith("gpt") else 4096)
        assistant = AssistantAgent(name="code_generator", model_client=model_client, system_message=system_prompt or self.default_system_prompt)
        code_blocks = []
        for _ in range(loop_times):
            try:
                st = asyncio.get_event_loop().time()
                response = await Console(assistant.on_messages_stream(messages=msgs, cancellation_token=CancellationToken()))
                et = asyncio.get_event_loop().time()
                print(f"It costs {et-st:.3f} seconds to generate code; prompt_tokens: {response.chat_message.models_usage.prompt_tokens}; completion_tokens: {response.chat_message.models_usage.completion_tokens}")
                code_blocks = extract_code_blocks(response.chat_message.content, ["cpp","diff"])
            except Exception as e:
                print(e)
                break
        return code_blocks    

class Merger:
    def __init__(self, config):
        self.config = config
        self.llm_config = get_model_config(self.config)
        self.prompt = None

    async def __call__(self, func, system_prompt=None, loop_times=1):
        msgs = [TextMessage(content=func, source="user")]    
        model_client = OpenAIChatCompletionClient(**self.llm_config.model_dump(), max_tokens=None if self.llm_config.model.startswith("gpt") else 1024)
        assistant = AssistantAgent(name="merger", model_client=model_client, system_message=system_prompt or self.prompt)
        for _ in range(loop_times):
            st = asyncio.get_event_loop().time()
            response = await Console(assistant.on_messages_stream(messages=msgs, cancellation_token=CancellationToken()))
            et = asyncio.get_event_loop().time()
            print(f"It costs {et-st:.3f} seconds to merge code; prompt_tokens: {response.chat_message.models_usage.prompt_tokens}; completion_tokens: {response.chat_message.models_usage.completion_tokens}")
            try:
                code = extract_code_blocks(response.chat_message.content, ["cpp", "diff"])
                return code
            except:
                continue

def TEST_complete_input_complete_output():
    ast = AST()
    src = "/home/jiangbo/arctic/arctic/src"
    include = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"]
    namespaces = None
    cache_file = "/home/jiangbo/agentflow/workspace/galsim7/cache"
    dir_list = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/arctic/src"]
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]
    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_file, load=True)

    code = ast.fetch_source_code(symbol="n_electrons_released", scope="TrapManagerInstantCapture", filters=output_filters, with_header=True, requires_whole_target_file=True)

    generator = Generator("/home/jiangbo/agentflow/docs/OAI_CONFIG_LIST.json")
    msgs = "### Input\n\n" + code
    result = asyncio.run(generator(msgs, GENERATE_COMPLETE_CODE_SYSTEM_PROMPT))
    print(result)

def TEST_complete_input_diff_output():
    ast = AST()
    src = "/home/jiangbo/arctic/arctic/src"
    include = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"]
    namespaces = None
    cache_file = "/home/jiangbo/agentflow/workspace/galsim7/cache"
    dir_list = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/arctic/src"]
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]
    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_file, load=True)

    code = ast.fetch_source_code(symbol="n_electrons_released", scope="TrapManagerInstantCapture", filters=output_filters, with_header=True, requires_whole_target_file=True)

    generator = Generator("/home/jiangbo/agentflow/docs/OAI_CONFIG_LIST.json")
    msgs = "### Input\n\n" + code
    result = asyncio.run(generator(msgs, system_prompt=GENERATE_UNIFIED_DIFF_SYSTEM_PROMPT))
    print(result)
    with NamedTemporaryFile(mode="wt", delete=True) as f:
        f.write(result[0])
        f.flush() # This is required, otherwise the file is still empty when the `patch` command is executed
        command = f"patch -o /tmp/new.cpp --ignore-whitespace /home/jiangbo/arctic/arctic/src/trap_managers.cpp {f.name}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)

def TEST_complete_input_snippet_output():
    ast = AST()
    src = "/home/jiangbo/arctic/arctic/src"
    include = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"]
    namespaces = None
    cache_file = "/home/jiangbo/agentflow/workspace/galsim7/cache"
    dir_list = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/arctic/src"]
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]
    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_file, load=True)

    complete_code = ast.fetch_source_code(symbol="n_electrons_released", scope="TrapManagerInstantCapture", filters=output_filters, with_header=True, requires_whole_target_file=True)

    generator = Generator("/home/jiangbo/agentflow/docs/OAI_CONFIG_LIST.json")
    merger = Merger("/home/jiangbo/agentflow/docs/OAI_CONFIG_LIST.json")
    msgs = "### Input\n\n" + complete_code
    result = asyncio.run(generator(msgs, GENERATE_CODE_SNIPPET_SYSTEM_PROMPT))
    print(result)

    with open("/home/jiangbo/arctic/arctic/src/trap_managers.cpp") as f:
        origin = f.read()

    msgs = \
"""
### Input    
1. the original file content
{origin}

2. the updated code snippets
{update_snippets}
"""  
    msgs = msgs.format(origin=origin, update_snippets=result[0])
    complete_code = asyncio.run(merger(msgs, MERGE_CODE_SNIPPETS_SYSTEM_PROMPT))
    print(complete_code)

def TEST_snippet_input_snippet_output():
    ast = AST()
    src = "/home/jiangbo/arctic/arctic/src"
    include = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"]
    namespaces = None
    cache_file = "/home/jiangbo/agentflow/workspace/galsim7/cache"
    dir_list = ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/arctic/src"]
    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]
    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=output_filters, cache_file=cache_file, load=True)

    complete_code = ast.fetch_source_code(symbol="n_electrons_released", scope="TrapManagerInstantCapture", filters=output_filters, with_header=True, requires_whole_target_file=False)

    generator = Generator("/home/jiangbo/agentflow/docs/OAI_CONFIG_LIST.json")
    merger = Merger("/home/jiangbo/agentflow/docs/OAI_CONFIG_LIST.json")
    msgs = "### Input\n\n" + complete_code
    result = asyncio.run(generator(msgs, GENERATE_CODE_SNIPPET_SYSTEM_PROMPT))
    print(result)

    with open("/home/jiangbo/arctic/arctic/src/trap_managers.cpp") as f:
        origin = f.read()

    msgs = \
"""
### Input    
1. the original file content
{origin}

2. the updated code snippets
{update_snippets}
"""  
    msgs = msgs.format(origin=origin, update_snippets=result[0])
    complete_code = asyncio.run(merger(msgs, MERGE_CODE_SNIPPETS_SYSTEM_PROMPT))
    print(complete_code)

if __name__ == '__main__':
    #TEST0()    
    #TEST_complete_input_complete_output()
    #TEST_complete_input_diff_output()
    #TEST_complete_input_snippet_output()
    TEST_snippet_input_snippet_output()