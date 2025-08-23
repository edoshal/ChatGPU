"""
Pinecone service for managing chat history as a vector store.
"""
import os
import logging
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import AzureOpenAIEmbeddings
from langchain_pinecone import Pinecone
from pinecone import Pinecone as PineconeClient

# Tải biến môi trường
load_dotenv()

# Cấu hình logger
logger = logging.getLogger("pinecone_db")


class PineconeService:
    def __init__(self):
        self.client: Optional[PineconeClient] = None
        self.index_name: str = os.getenv("PINECONE_INDEX_NAME", "chatgpu-history")
        self.embeddings: Optional[AzureOpenAIEmbeddings] = None
        self._initialized: bool = False

    def _initialize(self):
        """Khởi tạo kết nối đến Pinecone và mô hình embeddings một cách lười biếng (lazy)."""
        if self._initialized:
            return

        api_key = os.getenv("PINECONE_API_KEY")
        embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

        if not api_key or not embedding_deployment:
            logger.warning("PINECONE_API_KEY hoặc AZURE_OPENAI_EMBEDDING_DEPLOYMENT chưa được cấu hình. Dịch vụ Pinecone đã bị vô hiệu hóa.")
            return

        try:
            # Khởi tạo client Pinecone
            self.client = PineconeClient(api_key=api_key)

            # Khởi tạo mô hình embeddings
            self.embeddings = AzureOpenAIEmbeddings(
                azure_deployment=embedding_deployment,
                openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
            )

            # Kiểm tra và tạo index nếu cần
            if self.index_name not in self.client.list_indexes().names():
                embedding_dimension = len(self.embeddings.embed_query("test"))
                self.client.create_index(
                    name=self.index_name,
                    dimension=embedding_dimension,
                    metric="cosine",
                )
                logger.info(f"Đã tạo chỉ mục Pinecone '{self.index_name}' với chiều {embedding_dimension}.")
            
            self._initialized = True
            logger.info("Dịch vụ Pinecone đã được khởi tạo thành công.")

        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo dịch vụ Pinecone: {e}")
            self.client = None

    def get_vector_store(self) -> Optional[Pinecone]:
        """Lấy đối tượng LangChain VectorStore được kết nối với chỉ mục Pinecone."""
        self._initialize()
        if not self.client or not self.embeddings:
            return None
        
        return Pinecone.from_existing_index(self.index_name, self.embeddings)

    def is_available(self) -> bool:
        """Kiểm tra xem dịch vụ có được cấu hình và sẵn sàng không."""
        if not self._initialized:
            self._initialize()
        return self.client is not None

# Tạo một instance singleton để sử dụng trong toàn bộ ứng dụng
pinecone_service = PineconeService()

