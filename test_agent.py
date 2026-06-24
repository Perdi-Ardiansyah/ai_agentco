from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent  # pyrefly: ignore[deprecated]
import logging
logging.basicConfig(level=logging.INFO)

@tool
def check_stock() -> str:
    """cek stok"""
    return 'stok 10'

llm = ChatOllama(model='llama3.2', temperature=0)
agent = create_react_agent(llm, [check_stock])  # pyrefly: ignore[deprecated]
result = agent.invoke({'messages': [('user', 'cek stok saat ini')]})
print(result['messages'][-1].content)
