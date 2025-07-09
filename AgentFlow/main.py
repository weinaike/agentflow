
from autogen_agentchat.ui import Console
from autogen_ext.tools.mcp import StdioServerParams, StreamableHttpServerParams, SseServerParams
import logging
import asyncio
import argparse
from pathlib import Path

from .solution import Solution

logging.basicConfig(level=logging.WARNING)

def main():
    parser = argparse.ArgumentParser(description='Run the workflows')
    parser.add_argument('config', type=str, help='The configuration file for the workflows')
    parser.add_argument('--specific_flow','-f', nargs="+", type=str, help='The specific flow to run', default=[])
    parser.add_argument('--specific_node','-n', nargs="+", type=str, help='The specific node to run', default=[])
    parser.add_argument('--debug','-d', action='store_true', help='Run in debug mode')
    parser.add_argument('--stream', '-s', action='store_true', help='Run in streaming mode')  # 新增流式参数
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.info(args)
    logging.info("Running workflows with config file: {}".format(args.config))
    config_file = args.config
    sp_flow = args.specific_flow
    sp_node = args.specific_node

    workflows = Solution(config_file)
    config = workflows.dump_component()
    with open(config_file + '_component.json', 'w') as f:
        json_str = config.model_dump_json(indent=2)
        f.write(json_str)

    if args.stream:
        # 流式运行
        async def stream_main():
            # fetch_mcp_server = StdioServerParams(
            #     command="mcp-server-fetch",
            #     args=[],
            # )
            command_mcp_server = StreamableHttpServerParams(
                url="http://localhost:8080/mcp",
                headers={"Authorization": "Bearer YOUR_ACCESS_TOKEN"}
            )

            await workflows.register_tools(command_mcp_server)

            await Console(workflows.run_stream(specific_flow=sp_flow, specific_node=sp_node), output_stats=True)                
            
        asyncio.run(stream_main())
    else:
        asyncio.run(workflows.run(specific_flow=sp_flow, specific_node=sp_node))


if __name__ == "__main__":
    import subprocess
    command = "cd /home/jiangbo/GalSim && git clean -dxf include src && git checkout -- src/ && git checkout -- include"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    #print(result.returncode)
    #print(result.stdout)
    #print(result.stderr)

    main()