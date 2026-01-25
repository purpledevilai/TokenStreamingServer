import asyncio
from typing import List
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool


class think(BaseModel):
    """
    A reasoning tool that allows the agent to organize and articulate its thought process 
    before taking action. Use this tool to plan steps, analyze information, or work through 
    complex problems systematically.
    
    Call this tool whenever you need to:
    - Break down a complex task into smaller steps
    - Reason through what information you have vs what you need
    - Plan the sequence of API calls or actions to take
    - Analyze data or responses before deciding next steps
    - Think through edge cases or potential issues
    """
    thoughts: List[str] = Field(
        description="A list of strings where each string represents a single thought, observation, "
                    "reasoning step, or planned action. Each item should be a complete thought or "
                    "step that contributes to solving the current task. "
                    "Example: ['The user wants to retrieve data from an external API', "
                    "'I need to determine the correct endpoint and required parameters', "
                    "'I have the base URL and authentication credentials', "
                    "'I should first make a GET request to fetch the available options', "
                    "'Then I can filter the results based on the user\\'s criteria']"
    )


def think_func(thoughts: List[str], context: dict = None) -> str:
    if not thoughts:
        return "No thoughts provided. Please provide at least one thought or reasoning step."
    
    # Format the thoughts into a structured output
    formatted_thoughts = []
    for i, thought in enumerate(thoughts, 1):
        formatted_thoughts.append(f"{i}. {thought}")
    
    thoughts_text = "\n".join(formatted_thoughts)
    
    return f"Thoughts processed:\n\n{thoughts_text}\n\nReasoning complete. Proceed with the planned actions."


async def think_func_async(thoughts: List[str], context: dict = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: think_func(thoughts, context)
    )


think_tool = AgentTool(params=think, function=think_func_async, pass_context=False)

