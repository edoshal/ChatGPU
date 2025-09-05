# ChatGPU Health - Hệ thống tư vấn dinh dưỡng thông minh

Một hệ thống tư vấn dinh dưỡng đa người dùng sử dụng AI, cho phép quản lý hồ sơ sức khỏe cá nhân và nhận tư vấn thực phẩm dựa trên tình trạng sức khỏe.

## ✨ Tính năng chính

### 🔐 **Hệ thống đa người dùng**
- **Đăng ký/Đăng nhập** với email và mật khẩu
- **JWT Authentication** với bảo mật cao
- **Phân quyền** user và admin rõ ràng
- **Session management** với refresh token

### 👤 **Quản lý hồ sơ sức khỏe**
- **Nhiều hồ sơ** cho mỗi tài khoản (gia đình, cá nhân)
- **Thông tin chi tiết**: tuổi, giới tính, cân nặng, chiều cao
- **Tình trạng sức khỏe** được AI phân tích và cải thiện
- **Chuyển đổi hồ sơ** linh hoạt

### 📄 **Xử lý tài liệu y tế**
- **Upload PDF** hồ sơ khám bệnh
- **AI tự động phân tích** và tóm tắt nội dung
- **Lưu trữ an toàn** theo từng hồ sơ sức khỏe
- **Tra cứu lịch sử** tài liệu đã upload

### 🤖 **Chat tư vấn AI**
- **Azure OpenAI** làm chuyên gia dinh dưỡng chính
- **Tư vấn thực phẩm** dựa trên kiến thức AI và tình trạng sức khỏe
- **Function Calling** tự động cập nhật hồ sơ khi phát hiện thông tin mới
- **Tra cứu thực phẩm đặc thù** (món địa phương, đặc sản Việt Nam)
- **Gợi ý cụ thể** về lượng ăn, cách chế biến
- **Text-to-Speech đa nền tảng**: Azure Speech Service và Facebook MMS-TTS-VIE
- **LangChain Agent Architecture**: Agent thông minh tự quyết định sử dụng tools và truy xuất ngữ cảnh từ Pinecone.

### 🥗 **Cơ sở dữ liệu thực phẩm đặc thù**
- **Tập trung thực phẩm Việt Nam** (mắm ruốc, nem chua, rau răm...)
- **Thông tin chống chỉ định** chi tiết cho từng bệnh lý
- **Liều lượng khuyến nghị** phù hợp với người Việt
- **AI Function Calling** tra cứu khi cần thiết

### 👨‍💼 **Quản trị hệ thống**
- **Dashboard admin** với thống kê chi tiết
- **Quản lý thực phẩm** (thêm, sửa, xóa)
- **Theo dõi người dùng** và hoạt động
- **Xuất báo cáo** hệ thống

## 🚀 Cài đặt và chạy

### 1. **Chuẩn bị môi trường**

```bash
# Clone repository
git clone <repository-url>
cd ChatGPU

# Tạo Python virtual environment
python -m venv .venv

# Kích hoạt virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2. **Cấu hình biến môi trường**

Sao chép `env.example` thành `.env` và điền các giá trị cần thiết:

```bash
cp env.example .env
```

Nội dung tệp `.env`:
```env
# Security
SECRET_KEY=your-super-secret-jwt-key-here-should-be-very-long-and-random
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS (production)
ALLOWED_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com

# Azure OpenAI (BẮT BUỘC)
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-06-01
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini                 # Model cho chat
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small # Model cho embedding

# Pinecone (BẮT BUỘC)
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX_NAME=chatgpu-history

# Azure Speech Service (TÙY CHỌN cho tính năng Text-to-Speech)
AZURE_SPEECH_KEY=your-speech-service-key
AZURE_SPEECH_REGION=southeastasia
```

### 3. **Chạy ứng dụng**

```bash
# Kích hoạt virtual environment (nếu chưa)
source .venv/bin/activate  # Linux/Mac
# hoặc
.venv\Scripts\activate     # Windows

# Chạy server
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. **Truy cập ứng dụng**

- **Web App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Account**: `admin@example.com` / `admin123`

## 📚 Hướng dẫn sử dụng

### **Cho người dùng thông thường:**

1. **Đăng ký tài khoản** mới hoặc đăng nhập
2. **Tạo hồ sơ sức khỏe** với thông tin cá nhân
3. **Upload tài liệu y tế** (PDF) để AI phân tích
4. **Bắt đầu chat** để hỏi về thực phẩm và dinh dưỡng
5. **Tra cứu thực phẩm** trong cơ sở dữ liệu
6. **Sử dụng Text-to-Speech** với 2 lựa chọn: Azure (nút xám) hoặc Facebook MMS-TTS-VIE (nút xanh với chữ M)

### **Cho admin:**

1. **Đăng nhập** với tài khoản admin
2. **Xem thống kê** hệ thống ở trang Dashboard
3. **Quản lý thực phẩm** - thêm/sửa/xóa thông tin
4. **Theo dõi người dùng** và hoạt động
5. **Xuất báo cáo** (sắp có)

## 🏗️ Kiến trúc hệ thống

### **Kiến trúc AI (LangChain & Pinecone)**

Hệ thống sử dụng kiến trúc Agent tiên tiến để xử lý các yêu cầu phức tạp. Toàn bộ logic chatbot được quản lý bởi **LangChain Agent**, có khả năng tự quyết định sử dụng các công cụ (Tools) và truy xuất ngữ cảnh từ **Pinecone**.

> 🔗 **Xem chi tiết kiến trúc tại file [IMPLEMENTATION_DETAILS.md](./IMPLEMENTATION_DETAILS.md)**

### **Backend (FastAPI)**
- **RESTful API** với validation Pydantic
- **JWT Authentication** với role-based access
- **SQLite database** cho dữ liệu chính
- **File upload** và xử lý PDF

### **Frontend (Vanilla JS)**
- **Single Page Application** với hash routing
- **Responsive design** cho mobile và desktop
- **Modern UI/UX** với CSS animations
- **Progressive Web App** ready

### **Database Schema**
```
users (accounts chính)
├── health_profiles (hồ sơ sức khỏe)
│   ├── documents (tài liệu y tế)
│   └── chat_sessions (phiên tư vấn)
│       └── chat_messages (tin nhắn)
├── foods (cơ sở dữ liệu thực phẩm)
└── user_sessions (tracking đăng nhập)
```

## 🔧 API Endpoints

### **Authentication**
- `POST /api/auth/register` - Đăng ký
- `POST /api/auth/login` - Đăng nhập
- `GET /api/me` - Thông tin user hiện tại

### **Health Profiles**
- `GET /api/profiles` - Danh sách hồ sơ
- `POST /api/profiles` - Tạo hồ sơ mới
- `PUT /api/profiles/{id}` - Cập nhật hồ sơ
- `DELETE /api/profiles/{id}` - Xóa hồ sơ

### **Documents**
- `POST /api/profiles/{id}/documents` - Upload PDF
- `GET /api/profiles/{id}/documents` - Danh sách tài liệu
- `GET /api/documents/{id}` - Chi tiết tài liệu

### **Chat**
- `GET /api/profiles/{id}/chats` - Danh sách phiên chat
- `POST /api/profiles/{id}/chats` - Tạo phiên chat
- `POST /api/chats/{id}/messages` - Gửi tin nhắn

### **Text-to-Speech**
- `POST /api/tts/generate` - Tạo audio với Azure Speech Service
- `GET /api/speech/status` - Trạng thái Azure Speech Service
- `POST /api/mms-tts/generate` - Tạo audio với Facebook MMS-TTS-VIE
- `GET /api/mms-tts/status` - Trạng thái Facebook MMS-TTS-VIE



### **Foods (Admin only)**
- `GET /api/foods` - Danh sách thực phẩm
- `POST /api/foods` - Thêm thực phẩm
- `PUT /api/foods/{id}` - Cập nhật thực phẩm
- `DELETE /api/foods/{id}` - Xóa thực phẩm

### **Statistics**
- `GET /api/stats` - Thống kê hệ thống (admin)
- `GET /api/me/stats` - Thống kê cá nhân

## 🛡️ Bảo mật

- **Password hashing** với bcrypt
- **JWT tokens** với expiration
- **Role-based access control**
- **SQL injection protection** với parameterized queries
- **CORS configuration** cho production
- **Input validation** với Pydantic models

## 🔄 Cập nhật và phát triển

### **Tính năng sắp tới:**
- [ ] Chat AI real-time với WebSocket
- [ ] Phân tích hình ảnh thực phẩm
- [ ] Xuất báo cáo PDF
- [ ] Notification system
- [ ] Mobile app (React Native)
- [ ] Integration với wearable devices
- [ ] Thêm các model TTS khác (Google, Amazon Polly)

### **Cải tiến hiện tại:**
- [x] ✅ Database schema tối ưu
- [x] ✅ RESTful API chuẩn
- [x] ✅ Modern responsive UI
- [x] ✅ Multi-user với profiles
- [x] ✅ Admin management system
- [x] ✅ Security và authentication
- [x] ✅ Multi-platform Text-to-Speech (Azure + Facebook MMS-TTS-VIE)
- [x] ✅ Kiến trúc AI nâng cao với LangChain Agent và Pinecone Vector Store

## 📝 License

MIT License - xem file LICENSE để biết thêm chi tiết.

## 🤝 Đóng góp

Chúng tôi hoan nghênh mọi đóng góp! Vui lòng tạo issue hoặc pull request.

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub hoặc liên hệ team phát triển.

---

**ChatGPU Health** - Tư vấn dinh dưỡng thông minh cho cuộc sống khỏe mạnh! 🌱✨