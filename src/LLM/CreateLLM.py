from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from Models.LLMModel import get_model

DEFAULT_MODEL = "gpt-4.1"

def create_llm(model_id: Optional[str] = None, for_streaming: bool = False):
    if not model_id:
        return ChatOpenAI(model=DEFAULT_MODEL, stream_usage=True) if for_streaming else ChatOpenAI(model=DEFAULT_MODEL)

    llm_model = get_model(model_id)

    if llm_model.model_provider == "anthropic":
        return ChatAnthropic(model=llm_model.model)
    elif for_streaming:
        return ChatOpenAI(model=llm_model.model, stream_usage=True)
    else:
        return ChatOpenAI(model=llm_model.model)
