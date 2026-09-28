import asyncio
from backend.agent.llm import ChatMessage, GroqLLMProvider, OpenAILLMProvider, get_llm_provider

async def test_llm_factory():
    provider = get_llm_provider()
    # If no API key set in test env, factory returns None or configured instance
    print(f"LLM Provider instance: {provider}")
    
async def test_chat_message_dataclass():
    msg = ChatMessage(role="user", content="Hello, AI!")
    assert msg.role == "user"
    assert msg.content == "Hello, AI!"
    print("ChatMessage dataclass test passed.")

if __name__ == "__main__":
    asyncio.run(test_chat_message_dataclass())
    asyncio.run(test_llm_factory())
    print("All LLM unit tests passed successfully!")
