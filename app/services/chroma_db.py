"""
ChromaDB service for managing chat history and context
"""
import os
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
except RuntimeError as e:
    if "sqlite3" in str(e).lower():
        chromadb = None
    else:
        raise

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("chroma_db")


class ChromaDBService:
    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False
        self.db_path = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")
        
    def _initialize_service(self):
        """Khởi tạo ChromaDB service (lazy loading)"""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing ChromaDB service...")
            
            # Create ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection for chat history
            self.collection = self.client.get_or_create_collection(
                name="chat_history",
                metadata={"description": "Chat history for context management"}
            )
            
            self._initialized = True
            logger.info(f"ChromaDB service initialized successfully at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB service: {str(e)}")
            raise
    
    def add_chat_message(self, 
                        user_id: int, 
                        profile_id: int, 
                        chat_id: int,
                        message_id: int,
                        content: str, 
                        is_user: bool,
                        timestamp: Optional[str] = None) -> bool:
        """
        Thêm tin nhắn chat vào ChromaDB
        
        Args:
            user_id: ID của user
            profile_id: ID của health profile
            chat_id: ID của chat session
            message_id: ID của message
            content: Nội dung tin nhắn
            is_user: True nếu là tin nhắn từ user, False nếu từ AI
            timestamp: Thời gian tạo tin nhắn
            
        Returns:
            True nếu thành công, False nếu có lỗi
        """
        if not content or not content.strip():
            return False
            
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Tạo unique ID cho document
            doc_id = f"msg_{user_id}_{profile_id}_{chat_id}_{message_id}"
            
            # Tạo metadata
            metadata = {
                "user_id": user_id,
                "profile_id": profile_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "is_user": is_user,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
                "content_length": len(content),
                "content_hash": hashlib.md5(content.encode()).hexdigest()
            }
            
            # Thêm document vào collection
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added chat message to ChromaDB: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chat message to ChromaDB: {str(e)}")
            return False
    
    def get_chat_context(self, 
                        user_id: int, 
                        profile_id: int, 
                        chat_id: int,
                        query: str,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy context từ lịch sử chat dựa trên query hiện tại
        
        Args:
            user_id: ID của user
            profile_id: ID của health profile
            chat_id: ID của chat session
            query: Query hiện tại để tìm context liên quan
            limit: Số lượng kết quả trả về
            
        Returns:
            List các document có context liên quan
        """
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Tìm kiếm documents liên quan
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={
                    "user_id": user_id,
                    "profile_id": profile_id,
                    "chat_id": chat_id
                }
            )
            
            # Format kết quả
            context_messages = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    context_messages.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        "distance": results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                    })
            
            logger.info(f"Retrieved {len(context_messages)} context messages for query")
            return context_messages
            
        except Exception as e:
            logger.error(f"Error retrieving chat context: {str(e)}")
            return []
    
    def get_recent_chat_history(self, 
                               user_id: int, 
                               profile_id: int, 
                               chat_id: int,
                               limit: int = 20) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử chat gần đây nhất
        
        Args:
            user_id: ID của user
            profile_id: ID của health profile
            chat_id: ID của chat session
            limit: Số lượng tin nhắn gần đây nhất
            
        Returns:
            List các tin nhắn gần đây nhất
        """
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Lấy tất cả documents của chat session này
            results = self.collection.get(
                where={
                    "user_id": user_id,
                    "profile_id": profile_id,
                    "chat_id": chat_id
                },
                include=['metadatas', 'documents']
            )
            
            # Sort theo timestamp và lấy limit gần đây nhất
            if results['metadatas']:
                # Sort theo message_id (assume higher ID = newer message)
                sorted_data = sorted(
                    zip(results['metadatas'], results['documents']),
                    key=lambda x: int(x[0].get('message_id', 0)),
                    reverse=True
                )
                
                # Lấy limit gần đây nhất
                recent_messages = []
                for metadata, document in sorted_data[:limit]:
                    recent_messages.append({
                        "content": document,
                        "metadata": metadata
                    })
                
                # Reverse lại để có thứ tự thời gian đúng
                recent_messages.reverse()
                
                logger.info(f"Retrieved {len(recent_messages)} recent messages")
                return recent_messages
            
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving recent chat history: {str(e)}")
            return []
    
    def get_user_chat_summary(self, user_id: int, profile_id: int) -> Dict[str, Any]:
        """
        Lấy summary của tất cả chat sessions của user
        
        Args:
            user_id: ID của user
            profile_id: ID của health profile
            
        Returns:
            Summary của chat history
        """
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Lấy tất cả documents của user
            results = self.collection.get(
                where={
                    "user_id": user_id,
                    "profile_id": profile_id
                },
                include=['metadatas', 'documents']
            )
            
            if not results['metadatas']:
                return {
                    "total_messages": 0,
                    "chat_sessions": 0,
                    "user_messages": 0,
                    "ai_messages": 0,
                    "total_content_length": 0
                }
            
            # Tính toán statistics
            total_messages = len(results['metadatas'])
            chat_sessions = set()
            user_messages = 0
            ai_messages = 0
            total_content_length = 0
            
            for metadata in results['metadatas']:
                chat_sessions.add(metadata.get('chat_id', 0))
                if metadata.get('is_user', False):
                    user_messages += 1
                else:
                    ai_messages += 1
                total_content_length += metadata.get('content_length', 0)
            
            return {
                "total_messages": total_messages,
                "chat_sessions": len(chat_sessions),
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "total_content_length": total_content_length
            }
            
        except Exception as e:
            logger.error(f"Error getting user chat summary: {str(e)}")
            return {}
    
    def delete_chat_history(self, user_id: int, profile_id: int, chat_id: Optional[int] = None) -> bool:
        """
        Xóa lịch sử chat
        
        Args:
            user_id: ID của user
            profile_id: ID của health profile
            chat_id: ID của chat session (nếu None thì xóa tất cả)
            
        Returns:
            True nếu thành công, False nếu có lỗi
        """
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            where_clause = {
                "user_id": user_id,
                "profile_id": profile_id
            }
            
            if chat_id is not None:
                where_clause["chat_id"] = chat_id
            
            # Xóa documents
            self.collection.delete(where=where_clause)
            
            logger.info(f"Deleted chat history for user {user_id}, profile {profile_id}, chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chat history: {str(e)}")
            return False
    
    def is_available(self) -> bool:
        """Kiểm tra xem ChromaDB có khả dụng không"""
        return chromadb is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê của ChromaDB"""
        try:
            # Khởi tạo service nếu chưa được tải
            self._initialize_service()
            
            # Lấy thông tin collection
            collection_info = self.collection.count()
            
            return {
                "total_documents": collection_info,
                "collection_name": "chat_history",
                "db_path": self.db_path
            }
            
        except Exception as e:
            logger.error(f"Error getting ChromaDB stats: {str(e)}")
            return {}


# Singleton instance
chroma_service = ChromaDBService()


def add_chat_message(user_id: int, profile_id: int, chat_id: int, message_id: int, 
                    content: str, is_user: bool, timestamp: Optional[str] = None) -> bool:
    """Helper function để thêm tin nhắn chat"""
    return chroma_service.add_chat_message(user_id, profile_id, chat_id, message_id, 
                                          content, is_user, timestamp)


def get_chat_context(user_id: int, profile_id: int, chat_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Helper function để lấy chat context"""
    return chroma_service.get_chat_context(user_id, profile_id, chat_id, query, limit)


def get_recent_chat_history(user_id: int, profile_id: int, chat_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Helper function để lấy lịch sử chat gần đây"""
    return chroma_service.get_recent_chat_history(user_id, profile_id, chat_id, limit)


def is_chroma_available() -> bool:
    """Kiểm tra xem ChromaDB có khả dụng không"""
    return chromadb is not None and chroma_service.is_available() 