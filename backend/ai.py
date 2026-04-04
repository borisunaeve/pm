import httpx
import os
import json
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "openai/gpt-oss-120b")

class ChatMessage(BaseModel):
    role: str
    content: str
    
class KanbanAction(BaseModel):
    action: Literal["CREATE_CARD", "MOVE_CARD", "DELETE_CARD", "RENAME_COLUMN"] = Field(
        description="The action to perform on the Kanban board based on user request."
    )
    card_title: Optional[str] = Field(None, description="Title of the new card if creating one")
    card_details: Optional[str] = Field(None, description="Details/description for the new card")
    target_column: Optional[str] = Field(
        None, 
        description="The ID of the target column (e.g. 'col-backlog', 'col-done'). For CREATE_CARD, this defaults to 'col-backlog' if unspecified."
    )
    card_id: Optional[str] = Field(None, description="The ID of the card to move or delete")
    column_id: Optional[str] = Field(None, description="The ID of the column to rename")
    new_column_title: Optional[str] = Field(None, description="The new title for the column")

class KanbanResponse(BaseModel):
    response_message: str = Field(
        description="The conversational response to show the user in the chat UI"
    )
    actions: List[KanbanAction] = Field(
        description="A list of actions to perform on the Kanban board. Important: you must output an array."
    )

class ChatRequest(BaseModel):
    messages: list[ChatMessage]

async def call_openrouter(messages: list[ChatMessage], board_context: str = "", schema_name: str = "KanbanResponse") -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Project Management MVP",
    }
    
    # We define the JSON Schema using Pydantic's model_json_schema()
    raw_schema = KanbanResponse.model_json_schema()
    
    # OpenAI Structured Outputs with strict=True requires additionalProperties=False on all objects
    # It also requires the 'required' array to contain every key inside 'properties'.
    def enforce_strict_schema(schema_obj: dict):
        if isinstance(schema_obj, dict):
            if schema_obj.get("type") == "object" or "properties" in schema_obj:
                schema_obj["additionalProperties"] = False
                if "properties" in schema_obj:
                    # Every property must be listed in the required array
                    schema_obj["required"] = list(schema_obj["properties"].keys())
            for value in schema_obj.values():
                if isinstance(value, (dict, list)):
                    enforce_strict_schema(value)
        elif isinstance(schema_obj, list):
            for item in schema_obj:
                if isinstance(item, (dict, list)):
                    enforce_strict_schema(item)

    enforce_strict_schema(raw_schema)
    
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": raw_schema
        }
    }
    
    # Add an additional system prompt to give the AI context of available properties
    system_content = (
        "You are a helpful Project Management AI Assistant built into a Kanban board."
        " You can create, move, or delete cards, or rename columns when asked."
        " Always make sure the IDs you reference match the exact IDs provided."
        "\nAsk clarifying questions if card or column intents are ambiguous."
    )
    if board_context:
        system_content += f"\n\nCURRENT BOARD STATE:\n{board_context}"

    system_context = {
        "role": "system",
        "content": system_content
    }

    payload = {
        "model": AI_MODEL,
        "messages": [system_context] + [{"role": m.role, "content": m.content} for m in messages],
        "response_format": response_format,
        "temperature": 0.1,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        
        content_str = data["choices"][0]["message"]["content"]
        # The content should be a JSON string according to our response_format
        return json.loads(content_str)
