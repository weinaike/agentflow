import subprocess
from loguru import logger

from AgentFlow.tools.graph_service import MemgraphIngestor

from autogen_agentchat.agents import AssistantAgent

class TranslationAgent(AssistantAgent):

    def __init__(self):
        port_used = -1
        for port in range(9000, 9100):
            command = f"docker run -p {port}:7687 --name agentflow_trans_{port} -d memgraph/memgraph-mage"
            result = subprocess.run(command)
            if result.returncode == 0:
                port_used = port
                break
        if port_used == -1:
            logger.error("Can't start a memgraph service")
            raise RuntimeError("Can't start a memgraph service")
        self.ingestor = MemgraphIngestor("localhost", port_used)
                
    def get_topological_sorted_nodes(self):
        sort_query = """
        MATCH p=(n:Function)-[:CALLS]->(m:Function)
        WHERE m.out_of_scope = false
        WITH project(p) AS graph
        CALL graph_util.topological_sort(graph) YIELD sorted_nodes
        UNWIND sorted_nodes AS nodes
        RETURN properties(nodes) AS properties;
        """

        sort_query = """
        MATCH p=(n:Function)-[:CALLS]->(m:Function)
        WHERE n.out_of_scope = false AND m.out_of_scope = false
        WITH collect(p) AS rel_paths
        MATCH (isolated:Function)
        WHERE isolated.out_of_scope = false 
        AND NOT (isolated)-[:CALLS]->() 
        AND NOT ()-[:CALLS]->(isolated)
        WITH rel_paths, collect(isolated) AS isolated_nodes
        CALL graph_util.project(rel_paths) YIELD graph
        CALL graph_util.add_nodes(graph, isolated_nodes) YIELD graph AS full_graph
        CALL graph_util.topological_sort(full_graph) YIELD sorted_nodes
        UNWIND sorted_nodes AS node
        RETURN properties(node) AS properties;
        """
        sorted_nodes = self.ingestor.fetch_all(sort_query)

        return [sorted_node["properties"] for sorted_node in sorted_nodes]

    def get_callees(self, unique_id):
        query = """
        MATCH (n:Function)-[:CALLS]->(m:Function)
        WHERE n.unique_id = '{unique_id}'
        RETURN properties(m) as properties
        """
        callees = self.ingestor.fetch_all(query=query.format(unique_id=unique_id))
        return [callee["properties"] for callee in callees] if callees else []

    def get_callers(self, unique_id):
        query = """
        MATCH (n:Function)-[:CALLS]->(m:Function)
        WHERE m.unique_id = '{unique_id}'
        RETURN properties(n) as properties
        """
        callers = self.ingestor.fetch_all(query=query.format(unique_id=unique_id))
        return [caller["properties"] for caller in callers] if callers else []

    def get_node(self, unique_id):
        query = """
        MATCH (n:Function)
        WHERE n.unique_id = $unique_id
        RETURN properties(n) as properties
        """
        nodes = self.ingestor.fetch_all(query, params={"unique_id": unique_id})
        return [node["properties"] for node in nodes] if nodes else []

    def update_node(self, unique_id, properties):
        set_clause = ", ".join([f"n.{k} = ${k}" for k in properties.keys() if k != "unique_id"])
        if "unique_id" not in properties:
            properties["unique_id"] = unique_id
        query = """
        MATCH (n:Function {{unique_id: $unique_id}})
        SET {set_clause}
        RETURN properties(n) as properties
        """    
        updated_nodes = self.ingestor.fetch_all(query.format(set_clause=set_clause), properties)
        self.ingestor.flush_nodes()
        return [updated_node["properties"] for updated_node in updated_nodes] if updated_nodes else []

    def set_property(self, unique_id, name, value):
        query = """
        MATCH (n:Function)
        WHERE n.unique_id = $unique_id
        SET n.{name} = $value
        RETURN properties(n) as properties
        """    
        updated_nodes = self.ingestor.fetch_all(query=query.format(name=name), params={"unique_id": unique_id, "value": value})
        self.ingestor.flush_nodes()
        return [updated_node["properties"] for updated_node in updated_nodes] if updated_nodes else []

    def parse_project(self):
        pass

    def design_interface(self):
        pass
    
    def translate(self):
        pass
    
    def assemble(self):
        pass
    
    def run_stream(self, *, task = None, cancellation_token = None, output_task_messages = True):
        return super().run_stream(task=task, cancellation_token=cancellation_token, output_task_messages=output_task_messages)

