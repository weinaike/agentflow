#!/usr/bin/env python3
"""
独立的MCP服务端启动器
用于Docker容器中运行，避免相对导入问题
"""

import sys
import os
import logging
from mcp.server import FastMCP
from mcp.types import TextContent
from starlette.responses import Response, JSONResponse

from uml_tool import *
from code_tool import *
from shell_tool import *
from file_tool import *

# 配置日志
logger = logging.getLogger(__name__)

app = FastMCP('agentflow-mcp-server', version='1.0.0')

app.add_tool(generate_cpp_uml)
app.add_tool(extract_class_structure_from_uml)
app.add_tool(extract_Inheritance_classes_from_uml)
app.add_tool(extract_inter_class_relationship_from_uml)
app.add_tool(fetch_source_code)
app.add_tool(fetch_source_code_snippet)
app.add_tool(query_right_name)
app.add_tool(query_important_functions)
app.add_tool(file_edit_rollback_files)
app.add_tool(read_function_from_file)
app.add_tool(read_code_from_file)
app.add_tool(file_edit_save_to_file)
app.add_tool(run_command)
app.add_tool(write_file)
app.add_tool(read_file)
app.add_tool(list_directory)
app.add_tool(get_working_directory)
app.add_tool(get_environment)
app.add_tool(show_dir_content)
app.add_tool(get_cpp_dir_structure)
app.add_tool(get_dir_structure_with_tree_cmd)
app.add_tool(run_python_code)
app.add_tool(run_shell_code)
app.add_tool(read_file_content)

@app.custom_route("/health", methods=["GET"])
async def health_check(request) -> Response:
    """健康检查端点"""
    return JSONResponse({
        "status": "healthy",
        "service": "MCP Terminal Server",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    })

@app.custom_route("/api/tools", methods=["GET"])
async def list_available_tools(request) -> Response:
    """列出所有可用的工具"""
    tools = await app.list_tools()
    return JSONResponse({
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
            for tool in tools
        ]
    })


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    logger.info("Starting MCP Terminal Server...")
    app.settings.host = '0.0.0.0'
    app.settings.port = 8080  # 默认端口
    app.settings.streamable_http_path = "/mcp"  # MCP协议路径
    
    logger.info(f"Server will be available at:")
    logger.info(f"  - MCP Protocol: http://0.0.0.0:8080/mcp")
    logger.info(f"  - Health Check: http://0.0.0.0:8080/health")
    logger.info(f"  - API Tools: http://0.0.0.0:8080/api/tools")
    
    app.run(transport='streamable-http')
