from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Models import DataWindow, Agent

class open_data_window(BaseModel):
    """
    Open a DataWindow to access real-time cached data. DataWindows provide access to frequently updated information 
    like activity feeds, notifications, or live metrics. Once opened, the DataWindow will automatically refresh 
    with the latest data on each subsequent invocation, ensuring you always have current information without 
    making repeated tool calls.
    """
    data_window_id: str = Field(description="The unique identifier for the DataWindow to open.")

async def open_data_window_func(data_window_id: str, context: dict) -> str:
    """
    Opens a DataWindow and returns its current data.
    
    Args:
        data_window_id: The unique identifier for the DataWindow
        context: The context dict containing org_id for permission validation
        
    Returns:
        The current data from the DataWindow as a string
        
    Raises:
        Exception: If DataWindow doesn't exist or doesn't belong to the org
    """
    if not data_window_id:
        raise Exception("data_window_id is required.")

    # Get the agent from context's agent_id to get org_id for permission check
    agent = Agent.get_agent(context["agent_id"])
    if not agent:
        raise Exception(f"OpenDataWindow: Agent with id: {context.agent_id} does not exist")
    
    # Fetch the DataWindow
    data_window = DataWindow.get_data_window(data_window_id)
    
    # Validate org ownership
    if data_window.org_id != agent.org_id:
        raise Exception(f"OpenDataWindow: DataWindow {data_window_id} does not belong to your organization.", 403)
    
    return data_window.data

# This is the tool that will be used in the agent chat
open_data_window_tool = AgentTool(params=open_data_window, function=open_data_window_func, pass_context=True)

