import threading
from graphviz import Digraph
from collections import defaultdict
import re
import json

def thread_safe_singleton(cls):
    """线程安全的单实例装饰器"""
    instances = {}
    lock = threading.Lock()  # 锁，用于线程安全

    def get_instance(*args, **kwargs):
        nonlocal instances
        if cls not in instances:
            with lock:  # 确保实例化过程是线程安全的
                if cls not in instances:  # 双重检查，防止重复创建
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def calculate_degrees(graph: dict[str, list[str]]) -> dict[str, tuple[int, int]]:
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for node in graph:
        in_degree[node] = len(graph[node])
        for neighbor in graph[node]:
            out_degree[neighbor] += 1

    all_keys = set(in_degree.keys()).union(out_degree.keys())
    degree = {}
    for key in all_keys:
        first = 0
        second = 0
        if key in in_degree:
            first = in_degree[key]
        if key in out_degree:
            second = out_degree[key]
        degree[key] = (first, second)
    return degree



def draw_flow_graph(graph: dict[str, list[str]]) -> Digraph:        
    '''绘制流程图'''

    flow_name = 'graph'
    dot = Digraph(comment=flow_name)
    dot.attr(label=flow_name, labelloc='t', fontsize='20')

    # Add nodes to the graph
    for node in graph.keys():    
        dot.node(node.replace("::", "_"), node)
    
    # Add edges based on inputs
    for k, vals in graph.items():
        for val in vals:
            dot.edge(val.replace("::", "_"), k.replace("::", "_"))

    dot.render('graph', format='png', cleanup=True)

    return dot


def get_json_content(data:str) -> dict:
    code_block_pattern = re.compile(rf'```json(.*?)```', re.DOTALL)
    json_blocks = code_block_pattern.findall(data)
    json_content = json.loads(''.join(json_blocks))
    return json_content

from json import JSONEncoder
from datetime import datetime
class JsonHandler(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        return super().default(obj)    

    @staticmethod
    def deserialize(dct):    
        if "__datetime__" in dct:
            return datetime.fromisoformat(dct["__datetime__"])  
        return dct

if __name__ == '__main__':
    result = {
        "name": "alice",
        "grade": [98, 97],
        "date": datetime.now()
    }

    res = json.dumps(result, cls=JsonHandler)

    #res = json.loads(res, object_hook=JsonHandler.deserialize)
    res = json.loads(res)
    print(res)

    print(f"equal? {result == res}")