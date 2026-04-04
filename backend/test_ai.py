import asyncio
from dotenv import load_dotenv
from ai import call_openrouter, ChatMessage

load_dotenv()

async def test():
    messages = [
        ChatMessage(role="user", content="Add a card called 'Fix Tests' to the Backlog.")
    ]
    try:
        response = await call_openrouter(messages)
        print("SUCCESS:")
        print(response)
    except Exception as e:
        print("ERROR:")
        print(e)
        if hasattr(e, 'response'):
            print(e.response.text)

if __name__ == "__main__":
    asyncio.run(test())
