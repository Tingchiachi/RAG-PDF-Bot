# rag_chain.py
import time
import socket
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_qdrant import QdrantVectorStore
from sqlalchemy import create_engine

load_dotenv(".env")

# 初始化嵌入模型與 Qdrant 向量庫連線
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_Embedding_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_Embedding_DEPLOYMENT_NAME"),
    api_key=os.getenv("AZURE_OPENAI_Embedding_KEY"),
    openai_api_version=os.getenv("AZURE_OPENAI_Embedding_API_VERSION"),
)

qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
qdrant_host = "QDRANT"
qdrant_port = os.getenv("QDRANT_PORT")

def wait_for_qdrant(host="qdrant", port=qdrant_port, retries=20, delay=2):
    for attempt in range(retries):
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"Qdrant 已啟動（第 {attempt + 1} 次檢查）")
                return
        except OSError:
            print(f"Qdrant 尚未啟動，重試中 ({attempt + 1}/{retries})...")
            time.sleep(delay)
    raise RuntimeError("無法連接 Qdrant，請確認服務是否啟動")

wait_for_qdrant(host=qdrant_host, port=qdrant_port)

# 初始化 Qdrant 客戶端
qdrant_client = QdrantClient(url=qdrant_url)

# 初始化向量庫
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="pdf_document",
    embedding=embedding_model
)

# 初始化檢索器
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 2})

# 初始化 Azure OpenAI 聊天模型 (GPT4o)
azure_chat_model = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    max_tokens=512
)

# 建立提示樣板
q_template = ChatPromptTemplate.from_template("""
你是一個 PDF 文件問答小幫手，請根據下方提供的內容回答使用者的問題。
請使用繁體中文、簡潔扼要地回答。

【文件內容】
{context}

【使用者問題】
{input}
""")

document_chain = create_stuff_documents_chain(azure_chat_model, q_template)
retrieval_chain = create_retrieval_chain(retriever, document_chain)
engine = create_engine("sqlite:///./chat_history.db")

def get_session_history(session_id: str):
    return SQLChatMessageHistory(session_id=session_id, connection=engine)

# 建立檢索QA
qa_chain = RunnableWithMessageHistory(
    retrieval_chain,
    get_session_history,
    input_messages_key="input",
    output_messages_key="answer",
    history_messages_key="history"
)


def answer_query(query: str, session_id: str) -> str:
    sources = set()
    docs = retriever.invoke(query)
    for doc in docs:
        filename = doc.metadata.get("source", "unknown").lstrip("pdf document/")
        page = doc.metadata.get("page_label", "?")
        sources.add(f"{filename} 第 {page} 頁")
    response = qa_chain.invoke({"input": query}, config={"configurable": {"session_id": session_id}})
    response_answer = response["answer"]
    response_with_source = f"{response_answer}\n\n參考來源：{', '.join(sources)}"
    return response_with_source
   