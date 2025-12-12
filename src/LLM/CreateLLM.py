from langchain_openai import ChatOpenAI

def create_llm():
    llm = ChatOpenAI(
        model="gpt-4.1-2025-04-14"
    )
    return llm
