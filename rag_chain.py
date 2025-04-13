# rag_chain.py
import time
import socket
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_qdrant import QdrantVectorStore

load_dotenv(".env")

# 初始化嵌入模型與 Qdrant 向量庫連線
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_Embedding_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_Embedding_DEPLOYMENT_NAME"),
    api_key=os.getenv("AZURE_OPENAI_Embedding_KEY"),
    openai_api_version=os.getenv("AZURE_OPENAI_Embedding_API_VERSION"),
)

qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
qdrant_host = "qdrant"
qdrant_port = 6333

def wait_for_qdrant(host="qdrant", port=6333, retries=20, delay=2):
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
q_template = ChatPromptTemplate.from_template("""請根據以下參考資料回答問題：
參考資料：{context}
問題：{question}
""")

# 建立檢索QA
qa_chain = (
    {
        "context": retriever ,
        "question": RunnablePassthrough(),
    }
    | q_template
    | azure_chat_model
    | StrOutputParser()
)

def answer_query(query: str) -> str:
    result = qa_chain.invoke(query)
    return result
