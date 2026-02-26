import os
from AWS.DynamoDB import get_item, put_item, get_all_items
from pydantic import BaseModel

MODELS_TABLE_NAME = os.environ["MODELS_TABLE_NAME"]
MODELS_PRIMARY_KEY = "model"

class LLMModel(BaseModel):
    model: str
    model_provider: str
    input_token_cost: float
    output_token_cost: float

def get_model(model_name: str) -> LLMModel:
    item = get_item(MODELS_TABLE_NAME, MODELS_PRIMARY_KEY, model_name)
    if item is None:
        raise Exception(f"Model '{model_name}' not found in models table", 404)
    return LLMModel(**item)

def get_model_or_none(model_name: str) -> LLMModel | None:
    item = get_item(MODELS_TABLE_NAME, MODELS_PRIMARY_KEY, model_name)
    if item is None:
        return None
    return LLMModel(**item)

def get_all_models() -> list[LLMModel]:
    items = get_all_items(MODELS_TABLE_NAME)
    return [LLMModel(**item) for item in items]

def validate_model_id(model_id: str) -> None:
    """Validate that a model_id exists in the models table. Raises 400 if not found."""
    item = get_item(MODELS_TABLE_NAME, MODELS_PRIMARY_KEY, model_id)
    if item is None:
        raise Exception(f"Invalid model_id: '{model_id}' does not exist in the models table", 400)

def is_anthropic_model(model_id: str) -> bool:
    """Check if a model_id belongs to an Anthropic model."""
    model = get_model_or_none(model_id)
    return model is not None and model.model_provider == "anthropic"
