
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import  TextMentionTermination
from dotenv import load_dotenv
import json

load_dotenv("docs/.env")

agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-mini", 
        ), 
    ) 
agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
config = agent_team.dump_component()
print(config.model_dump_json())
json_str = config.model_dump_json(indent=2)
with open("weather_agent_team.json", "w") as f:
    f.write(json_str)