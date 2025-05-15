import os
from datetime import datetime
import uuid
from AWS.DynamoDB import get_item, put_item, delete_item, get_all_items_by_index
from AWS.CloudWatchLogs import get_logger
from pydantic import BaseModel
from typing import Optional
from Models import User

logger = get_logger(log_level=os.environ["LOG_LEVEL"])

CHAT_PAGES_TABLE_NAME = os.environ["CHAT_PAGES_TABLE_NAME"]
CHAT_PAGES_PRIMARY_KEY = os.environ["CHAT_PAGES_PRIMARY_KEY"]

class ChatPageStyle(BaseModel):
    background_color: str
    heading_color: str
    description_color: str
    button_background_color: str
    button_text_color: str
    button_hover_background_color: str
    button_hover_text_color: str

class ChatBoxStyle(BaseModel):
    background_color: str
    border_color: str
    ai_message_background_color: str
    ai_message_text_color: str
    user_message_background_color: str
    user_message_text_color: str
    user_input_background_color: str
    user_input_textarea_background_color: str
    user_input_textarea_text_color: str
    user_input_textarea_focus_color: str
    user_input_textarea_placeholder_text: str
    user_input_textarea_placeholder_color: str
    user_input_send_button_color: str
    user_input_send_button_hover_color: str
    user_input_send_button_text_color: str
    typing_indicator_background_color: str
    typing_indicator_dot_color: str

class ChatPageButton(BaseModel):
    label: str
    link: str

class ChatPage(BaseModel):
    chat_page_id: str
    org_id: str
    agent_id: str
    heading: str
    description: Optional[str] = None
    chat_page_style: ChatPageStyle
    chat_box_style: ChatBoxStyle
    buttons: Optional[list[ChatPageButton]] = []
    created_at: int
    updated_at: int

class CreateChatPageParams(BaseModel):
    agent_id: str
    org_id: Optional[str] = None
    heading: str
    description: Optional[str] = None
    chat_page_style: ChatPageStyle
    chat_box_style: ChatBoxStyle
    buttons: Optional[list[ChatPageButton]] = []

class UpdateChatPageParams(BaseModel):
    agent_id: Optional[str] = None
    heading: Optional[str] = None
    description: Optional[str] = None
    chat_page_style: Optional[ChatPageStyle] = None
    chat_box_style: Optional[ChatBoxStyle] = None
    buttons: Optional[list[ChatPageButton]] = None

def chat_page_exists(chat_page_id: str) -> bool:
    return get_item(CHAT_PAGES_TABLE_NAME, CHAT_PAGES_PRIMARY_KEY, chat_page_id) != None
    
def create_chat_page(create_chat_page: CreateChatPageParams) -> ChatPage:
    chat_page_data = {
        CHAT_PAGES_PRIMARY_KEY: str(uuid.uuid4()),
        "created_at": int(datetime.timestamp(datetime.now())),
        "updated_at": int(datetime.timestamp(datetime.now()))
    }
    chat_page_data.update(create_chat_page.model_dump())
    chat_page = ChatPage(**chat_page_data)
    put_item(CHAT_PAGES_TABLE_NAME, chat_page_data)
    return chat_page

def get_chat_page(chat_page_id: str) -> ChatPage:
    item = get_item(CHAT_PAGES_TABLE_NAME, CHAT_PAGES_PRIMARY_KEY, chat_page_id)
    if item is None:
        raise Exception(f"Chat Page with id: {chat_page_id} does not exist", 404)
    return ChatPage(**item)

def save_chat_page(chat_page: ChatPage) -> None:
    chat_page.updated_at = int(datetime.timestamp(datetime.now()))
    put_item(CHAT_PAGES_TABLE_NAME, chat_page.model_dump())

def delete_chat_page(chat_page_id: str) -> None:
    delete_item(CHAT_PAGES_TABLE_NAME, CHAT_PAGES_PRIMARY_KEY, chat_page_id)

def parse_chat_page_items(items: list[dict]) -> list[ChatPage]:
    chat_pages = []
    for item in items:
        try:
            chat_pages.append(ChatPage(**item))
        except Exception as e:
            logger.error(f"Error parsing chat page: {e}")
    return chat_pages

def get_chat_pages_in_org(org_id: str) -> list[ChatPage]:
    items = get_all_items_by_index(CHAT_PAGES_TABLE_NAME, "org_id", org_id)
    return parse_chat_page_items(items)

def delete_all_chat_pages_for_org(org_id: str) -> None:
    chat_pages = get_chat_pages_in_org(org_id)
    for chat_page in chat_pages:
        delete_chat_page(chat_page.chat_page_id)


