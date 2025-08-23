# Chi tiết triển khai kiến trúc LangChain & Pinecone

Tài liệu này giải thích chi tiết về kiến trúc kỹ thuật đằng sau chatbot, tập trung vào việc tích hợp LangChain và Pinecone.

## 1. Tổng quan kiến trúc

Hệ thống đã được nâng cấp từ một luồng xử lý chatbot thủ công sang kiến trúc dựa trên **LangChain Agent**. Luồng xử lý một tin nhắn mới như sau:

1.  **FastAPI Endpoint (`/api/chats/{session_id}/messages`)**: Tiếp nhận yêu cầu từ người dùng.
2.  **Context Retrieval**: Sử dụng **Pinecone** làm Vector Store để truy xuất lịch sử trò chuyện và các ngữ cảnh liên quan.
3.  **LangChain Agent (`langchain_agent.py`)**: Xây dựng một `AgentExecutor` với các thông tin sau:
    *   Mô hình ngôn ngữ (Azure OpenAI).
    *   Ngữ cảnh từ Pinecone và DB.
    *   Thông tin hồ sơ người dùng.
    *   Các công cụ (Tools) có sẵn.
4.  **Tool Execution**: Agent tự quyết định khi nào cần gọi các tool như `search_food_database` hoặc `update_health_status`.
5.  **Final Response**: Agent tổng hợp thông tin từ tool và kiến thức nền để tạo ra câu trả lời cuối cùng và gửi lại cho người dùng.

---

## 2. Tích hợp LangChain Agent (`app/services/langchain_agent.py`)

Đây là bộ não của chatbot, thay thế hoàn toàn logic `chat_with_food_tools` trước đây.

### ChatPromptTemplate

Chúng tôi sử dụng `ChatPromptTemplate` để cấu trúc thông tin đầu vào cho Agent. Đây là thành phần cốt lõi quyết định cách Agent suy nghĩ và hành động:

```python
prompt = ChatPromptTemplate.from_messages([
    # 1. Vai trò và hướng dẫn tổng thể cho AI
    ("system", system_prompt_template),
    # 2. "Chỗ giữ chỗ" cho lịch sử trò chuyện
    MessagesPlaceholder(variable_name="chat_history"),
    # 3. Câu hỏi hiện tại của người dùng
    ("human", "{input}"),
    # 4. "Giấy nháp" để Agent suy nghĩ và ghi lại các bước gọi tool
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
```

*   `system_prompt_template`: Chứa vai trò, nhiệm vụ và thông tin hồ sơ người dùng.
*   `chat_history`: Giúp Agent "nhớ" cuộc hội thoại.
*   `agent_scratchpad`: Vùng suy nghĩ của Agent, nơi nó ghi lại các lần gọi tool và kết quả, giúp nó đưa ra quyết định cho bước tiếp theo.

### Tools và Function Calling

Các hàm nghiệp vụ được định nghĩa là `tool` bằng decorator `@tool` của LangChain.

*   `search_food_database`: Tra cứu thông tin thực phẩm.
*   `update_health_status`: Cập nhật hồ sơ sức khỏe người dùng.

Để truyền ngữ cảnh (như `user_id`, `profile_id`) vào tool `update_health_status`, chúng tôi sử dụng `functools.partial` để "gói" các tham số này vào tool trước khi đưa cho Agent.

---

## 3. Tích hợp Pinecone (`app/services/pinecone_db.py`)

Hệ thống sử dụng Pinecone làm Vector Store chính cho môi trường production, thay thế cho ChromaDB.

*   **`PineconeService`**: Một class singleton quản lý kết nối, khởi tạo index và cung cấp một `VectorStore` của LangChain.
*   **Khởi tạo Index**: Dịch vụ tự động kiểm tra và tạo index Pinecone nếu nó chưa tồn tại. Chiều của vector được lấy tự động từ mô hình embedding của Azure OpenAI.
*   **Retriever**: Trong `api.py`, chúng tôi sử dụng `vector_store.as_retriever()` để tạo một retriever. Retriever này được cấu hình để lọc các vector theo `user_id`, `profile_id`, và `chat_id`, đảm bảo rằng mỗi người dùng chỉ truy xuất được ngữ cảnh của chính mình trong phiên trò chuyện hiện tại.

### Luồng lưu trữ và truy xuất ngữ cảnh

1.  **Lưu trữ**: Sau mỗi lượt hội thoại, cả tin nhắn của người dùng và phản hồi của AI đều được `vector_store.add_texts()` để thêm vào Pinecone. Mỗi vector được gắn metadata (`user_id`, `profile_id`, `chat_id`, `role`).
2.  **Truy xuất**: Khi có tin nhắn mới, `retriever.get_relevant_documents()` được gọi để tìm kiếm các đoạn hội thoại có liên quan nhất dựa trên sự tương đồng về ngữ nghĩa, có lọc theo metadata.
