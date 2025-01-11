
from .work_flow import Workflows
import logging
import asyncio
import argparse

logging.basicConfig(level=logging.WARNING)

def main():
    parser = argparse.ArgumentParser(description='Run the workflows')
    parser.add_argument('config', type=str, help='The configuration file for the workflows')
    parser.add_argument('--specific_flow','-f', nargs="+", type=str, help='The specific flow to run', default=[])
    parser.add_argument('--specific_node','-n', nargs="+", type=str, help='The specific node to run', default=[])
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    args = parser.parse_args()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    print(args)
    config_file = args.config
    sp_flow = args.specific_flow
    sp_node = args.specific_node
    print(sp_flow, sp_node)
    workflows = Workflows(config_file)
    asyncio.run(workflows.run(specific_flow=sp_flow, specific_node=sp_node))

if __name__ == "__main__":
    main()