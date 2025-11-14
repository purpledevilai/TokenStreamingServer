import os
from datetime import datetime
import uuid
from AWS.DynamoDB import get_item, get_items_by_scan, put_item, delete_item, get_all_items_by_index
from AWS.CloudWatchLogs import get_logger
from pydantic import BaseModel
from typing import Optional
from Models import User, Tool
from Tools import ToolRegistry

logger = get_logger(log_level=os.environ["LOG_LEVEL"])

AGENTS_TABLE_NAME = os.environ["AGENTS_TABLE_NAME"]
AGENTS_PRIMARY_KEY = os.environ["AGENTS_PRIMARY_KEY"]

class Agent(BaseModel):
    agent_id: str
    agent_name: str
    agent_description: str
    prompt: str
    org_id: str
    is_public: bool
    is_default_agent: bool
    agent_speaks_first: bool = False
    tools: Optional[list[str]] = []
    uses_prompt_args: Optional[bool] = False
    voice_id: Optional[str] = None
    initialize_tool_id: Optional[str] = None
    created_at: int
    updated_at: int

class HistoryAgent(BaseModel):
    agent_id: str
    agent_name: str
    agent_description: str

class CreateAgentParams(BaseModel):
    agent_name: str
    agent_description: str
    prompt: str
    org_id: Optional[str] = None
    is_public: bool
    agent_speaks_first: bool
    tools: Optional[list[str]] = []
    uses_prompt_args: Optional[bool] = False
    voice_id: Optional[str] = None
    initialize_tool_id: Optional[str] = None

class UpdateAgentParams(BaseModel):
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    prompt: Optional[str] = None
    is_public: Optional[bool] = None
    agent_speaks_first: Optional[bool] = None
    tools: Optional[list[str]] = None
    uses_prompt_args: Optional[bool] = None
    voice_id: Optional[str] = None
    initialize_tool_id: Optional[str] = None

def agent_exists(agent_id: str) -> bool:
    return get_item(AGENTS_TABLE_NAME, AGENTS_PRIMARY_KEY, agent_id) != None
    
def create_agent(
        agent_name: str,
        agent_description: str,
        prompt: str,
        org_id: str,
        is_public: bool,
        agent_speaks_first: bool,
        tools: Optional[list[str]] = [],
        uses_prompt_args: Optional[bool] = False,
        voice_id: Optional[str] = None,
        initialize_tool_id: Optional[str] = None
    ) -> Agent:
    agentData = {
        AGENTS_PRIMARY_KEY: str(uuid.uuid4()),
        "agent_name": agent_name,
        "agent_description": agent_description,
        "prompt": prompt,
        "org_id": org_id,
        "is_public": is_public,
        "agent_speaks_first": agent_speaks_first,
        "is_default_agent": False,
        "tools": tools,
        "uses_prompt_args": uses_prompt_args,
        "voice_id": voice_id,
        "initialize_tool_id": initialize_tool_id,
        "created_at": int(datetime.timestamp(datetime.now())),
        "updated_at": int(datetime.timestamp(datetime.now())),
    }
    agent = Agent(**agentData)
    put_item(AGENTS_TABLE_NAME, agentData)
    return agent

def get_agent(agent_id: str) -> Agent:
    item = get_item(AGENTS_TABLE_NAME, AGENTS_PRIMARY_KEY, agent_id)
    if item is None:
        raise Exception(f"Agent with id: {agent_id} does not exist", 404)
    return Agent(**item)

def save_agent(agent: Agent) -> None:
    agent.updated_at = int(datetime.timestamp(datetime.now()))
    put_item(AGENTS_TABLE_NAME, agent.model_dump())

def delete_agent(agent_id: str) -> None:
    delete_item(AGENTS_TABLE_NAME, AGENTS_PRIMARY_KEY, agent_id)

def get_agent_for_user(agent_id: str, user: User.User) -> Agent:
    agent = get_agent(agent_id)
    if (agent.is_public):
        return agent
    if (agent.org_id == "default"):
        return agent
    if (agent.org_id in user.organizations):
        return agent
    raise Exception(f"Agent does not belong to user's orgs", 403)

def parse_agent_items(items: list[dict]) -> list[Agent]:
    agents = []
    for item in items:
        try:
            agents.append(Agent(**item))
        except Exception as e:
            logger.error(f"Error parsing agent: {e}")
    return agents

def get_agents_from_ids(agent_ids: list[str]) -> list[Agent]:
    items = get_items_by_scan(AGENTS_TABLE_NAME, AGENTS_PRIMARY_KEY, agent_ids)
    return parse_agent_items(items)

def get_agents_in_org(org_id: str) -> list[Agent]:
    items = get_all_items_by_index(AGENTS_TABLE_NAME, "org_id", org_id)
    return parse_agent_items(items)

def get_default_agents() -> list[Agent]:
    itmes = get_all_items_by_index(AGENTS_TABLE_NAME, "org_id", "default")
    return parse_agent_items(itmes)

def get_public_agent(agent_id: str) -> Agent:
    agent = get_agent(agent_id)
    if (agent.is_public):
        return agent
    raise Exception(f"Agent is not public", 403)

def transform_to_history_agent(agent: Agent) -> HistoryAgent:
    return HistoryAgent(
        agent_id=agent.agent_id,
        agent_name=agent.agent_name,
        agent_description=agent.agent_description
   )

def delete_agents_in_org(org_id: str) -> None:
    agents = get_agents_in_org(org_id)
    for agent in agents:
        delete_agent(agent.agent_id)


