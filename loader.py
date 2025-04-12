# loader.py
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import AzureChatOpenAI,AzureOpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

# 載入環境變數
from dotenv import load_dotenv
load_dotenv(".env")

# 1. 讀取整個 pdf_documents 資料夾下的所有 PDF
pdf_folder = "pdf document"
all_documents = []

for filename in os.listdir(pdf_folder):
    if filename.lower().endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, filename)
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()  # 每頁作為一個 Document
        all_documents.extend(documents)

print(f"共載入 {len(all_documents)} 頁 PDF 文件")

# 2. 將文件切分為較小段落
text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
docs = text_splitter.split_documents(all_documents)

# 3. 初始化 OpenAI Embeddings (使用 Azure OpenAI 或 OpenAI API)
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_Embedding_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_Embedding_DEPLOYMENT_NAME"),
    api_key=os.getenv("AZURE_OPENAI_Embedding_KEY"),
    openai_api_version=os.getenv("AZURE_OPENAI_Embedding_API_VERSION"),
)
# 4. 將文件向量嵌入並存入 Qdrant 向量資料庫
qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
vector_store = QdrantVectorStore.from_documents(
    docs, 
    embedding_model, 
    url=qdrant_url,
    collection_name="pdf_document"
)
print(f"Inserted {len(docs)} documents into Qdrant vector store.")
