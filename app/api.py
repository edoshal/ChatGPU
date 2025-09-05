from typing import Any, Dict, List, Optional
import os
import hashlib
import secrets
from datetime import datetime, timedelta
import json
import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from jose import jwt, JWTError
from langchain_core.messages import HumanMessage, AIMessage
from passlib.context import CryptContext

from .services import db
from .services import pdf as pdfsvc
from .services import azure_openai as llm
from .services import langchain_agent
from .services import tts
from .services import mms_tts
from .services import health_planner

from .services import pinecone_db
from .models.schema import (
    HealthPlanCreate, HealthPlanUpdate, ActivityLog, MealLog,
    GoalType, PlanStatus, IntensityLevel, MealType, ActivityUpdate
)


# Setup logger
logger = logging.getLogger(__name__)


# ====== APP SETUP ======
app = FastAPI(
    title="ChatGPU Health Food Chatbot API",
    description="Multi-user health chatbot with food recommendations",
    version="2.0.0"
)

# CORS cấu hình cho production
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ====== PYDANTIC MODELS ======
class UserRegister(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)

class UserLogin(BaseModel):
    email: str
    password: str

class HealthProfileCreate(BaseModel):
    profile_name: str = Field(..., min_length=1)
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    weight: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    conditions_text: str = ""
    conditions_list: Optional[List[str]] = None
    is_default: bool = False

class HealthProfileUpdate(BaseModel):
    profile_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    weight: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    conditions_text: Optional[str] = None
    conditions_list: Optional[List[str]] = None
    is_default: Optional[bool] = None

class ChatMessageCreate(BaseModel):
    content: str
    message_type: str = Field("text", pattern="^(text|image|file)$")
    image_data: Optional[str] = None  # Base64 encoded image
    auto_play_response: bool = False  # Tự động phát âm thanh response

class FoodCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    nutrients: Optional[Dict[str, Any]] = {}
    contraindications: Optional[List[str]] = []
    benefits: Optional[List[str]] = []
    recommended_portions: Optional[Dict[str, Any]] = {}
    preparation_notes: Optional[str] = None


# ====== AUTH FUNCTIONS ======
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT and return current user"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def require_admin(current_user=Depends(get_current_user)):
    """Require admin role"""
    # current_user là sqlite3.Row, truy cập qua key
    if (current_user["role"] if isinstance(current_user, dict) else current_user["role"]) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def get_user_profile(profile_id: int, current_user=Depends(get_current_user)):
    """Get health profile with ownership validation"""
    profile = db.get_health_profile(profile_id, current_user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found or access denied")
    return profile


# ====== STARTUP ======
@app.on_event("startup")
def on_startup():
    db.init_db(seed=True)

    # Tạo admin account mặc định nếu chưa có
    admin = db.get_user_by_email("admin@example.com")
    if not admin:
        admin_id = db.create_user(
            email="admin@example.com",
            password_hash=pwd_context.hash("admin123"),
            full_name="System Admin",
            role="admin"
        )
        # Tạo profile mặc định cho admin
        db.create_health_profile(
            user_id=admin_id,
            profile_name="Admin Profile",
            is_default=True
        )
        print("✅ Created default admin: admin@example.com / admin123")


# (Mount static sẽ thực hiện ở cuối file để không che các API routes)


# ====== PUBLIC ENDPOINTS ======
@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/api/auth/register")
def register(data: UserRegister):
    """Đăng ký tài khoản mới"""
    # Check if user exists
    existing = db.get_user_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    # Create user
    password_hash = pwd_context.hash(data.password)
    user_id = db.create_user(
        email=data.email,
        password_hash=password_hash,
        full_name=data.full_name
    )

    # Create default profile
    profile_id = db.create_health_profile(
        user_id=user_id,
        profile_name="Hồ sơ chính",
        is_default=True
    )

    # Generate token
    token = create_access_token({"sub": str(user_id)})

    return {
        "message": "Đăng ký thành công",
        "token": token,
        "user": {
            "id": user_id,
            "email": data.email,
            "full_name": data.full_name,
            "default_profile_id": profile_id
        }
    }

@app.post("/api/auth/login")
def login(data: UserLogin):
    """Đăng nhập"""
    user = db.get_user_by_email(data.email)
    if not user or not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    # Update login time
    db.update_user_login(user["id"])

    # Generate token
    token = create_access_token({"sub": str(user["id"])})

    # Get default profile
    default_profile = db.get_default_health_profile(user["id"])

    return {
        "message": "Đăng nhập thành công",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "default_profile_id": default_profile["id"] if default_profile else None
        }
    }


# ====== USER PROFILE ENDPOINTS ======
@app.get("/api/me")
def get_current_user_info(current_user=Depends(get_current_user)):
    """Lấy thông tin user hiện tại"""
    profiles = db.list_health_profiles(current_user["id"])
    default_profile = db.get_default_health_profile(current_user["id"])

    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "last_login_at": current_user["last_login_at"],
        "profiles_count": len(profiles),
        "default_profile_id": default_profile["id"] if default_profile else None
    }

@app.get("/api/profiles")
def list_user_profiles(current_user=Depends(get_current_user)):
    """Lấy danh sách hồ sơ sức khỏe"""
    profiles = db.list_health_profiles(current_user["id"])
    return [dict(p) for p in profiles]

@app.post("/api/profiles")
def create_profile(data: HealthProfileCreate, current_user=Depends(get_current_user)):
    """Tạo hồ sơ sức khỏe mới"""

    # Process conditions with AI if provided
    conditions_json = {}
    if data.conditions_text:
        try:
            conditions_json = llm.process_medical_conditions(data.conditions_text)
        except Exception as e:
            # Fallback nếu AI service lỗi
            conditions_json = {"raw_text": data.conditions_text, "error": str(e)}
    # Merge thêm conditions_list nếu có
    if data.conditions_list:
        if not isinstance(conditions_json, dict):
            conditions_json = {}
        conditions_json["conditions_list"] = data.conditions_list

    profile_id = db.create_health_profile(
        user_id=current_user["id"],
        profile_name=data.profile_name,
        age=data.age,
        gender=data.gender,
        weight=data.weight,
        height=data.height,
        conditions_text=data.conditions_text,
        conditions_json=conditions_json,
        is_default=data.is_default
    )

    return {"message": "Tạo hồ sơ thành công", "profile_id": profile_id}

@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: int, profile=Depends(get_user_profile)):
    """Lấy chi tiết hồ sơ sức khỏe"""
    result = dict(profile)
    # Parse conditions_json safely
    try:
        if profile["conditions_json"]:
            import json as _json
            result["conditions_json"] = _json.loads(profile["conditions_json"]) if isinstance(profile["conditions_json"], str) else profile["conditions_json"]
        else:
            result["conditions_json"] = {}
    except Exception:
        result["conditions_json"] = {}

    return result

@app.put("/api/profiles/{profile_id}")
def update_profile(profile_id: int, data: HealthProfileUpdate, current_user=Depends(get_current_user)):
    """Cập nhật hồ sơ sức khỏe"""

    # Validate ownership
    profile = db.get_health_profile(profile_id, current_user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Prepare updates
    updates = {}
    for field, value in data.dict(exclude_unset=True).items():
        updates[field] = value

    # Process conditions if updated
    if "conditions_text" in updates and updates["conditions_text"]:
        try:
            updates["conditions_json"] = llm.process_medical_conditions(updates["conditions_text"])
        except Exception as e:
            updates["conditions_json"] = {"raw_text": updates["conditions_text"], "error": str(e)}
    if "conditions_list" in updates and updates["conditions_list"] is not None:
        cj = updates.get("conditions_json") or {}
        if not isinstance(cj, dict):
            cj = {}
        cj["conditions_list"] = updates["conditions_list"]
        updates["conditions_json"] = cj

    success = db.update_health_profile(profile_id, current_user["id"], **updates)
    if not success:
        raise HTTPException(status_code=400, detail="Update failed")

    return {"message": "Cập nhật hồ sơ thành công"}

@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: int, current_user=Depends(get_current_user)):
    """Xóa hồ sơ sức khỏe"""

    # Check if it's the only profile
    profiles = db.list_health_profiles(current_user["id"])
    if len(profiles) <= 1:
        raise HTTPException(status_code=400, detail="Không thể xóa hồ sơ cuối cùng")

    success = db.delete_health_profile(profile_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"message": "Xóa hồ sơ thành công"}


# ====== DOCUMENTS ENDPOINTS ======
@app.post("/api/profiles/{profile_id}/documents")
async def upload_document(
    profile_id: int,
    file: UploadFile = File(...),
    profile=Depends(get_user_profile)
):
    """Upload tài liệu y tế"""

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF")

    # Read and process PDF
    content = await file.read()

    try:
        # Extract text from PDF
        extracted_text = pdfsvc.extract_text_from_pdf(content)

        # Summarize with AI
        ai_summary = llm.summarize_medical_document(extracted_text)

        # Save to database
        doc_id = db.add_document(
            health_profile_id=profile_id,
            filename=file.filename,
            original_content=extracted_text,
            ai_summary=ai_summary,
            file_type="pdf",
            file_size=len(content)
        )

        return {
            "message": "Upload tài liệu thành công",
            "document_id": doc_id,
            "summary": ai_summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý tài liệu: {str(e)}")

@app.get("/api/profiles/{profile_id}/documents")
def list_profile_documents(profile_id: int, profile=Depends(get_user_profile)):
    """Lấy danh sách tài liệu của profile"""
    documents = db.list_documents(profile_id)
    return documents

@app.get("/api/documents/{doc_id}")
def get_document_detail(doc_id: int, current_user=Depends(get_current_user)):
    """Lấy chi tiết tài liệu (với ownership check qua profile)"""
    # Complex ownership check through profile
    with db.get_conn() as conn:
        doc = conn.execute("""
            SELECT d.*, hp.user_id
            FROM documents d
            JOIN health_profiles hp ON d.health_profile_id = hp.id
            WHERE d.id = ? AND hp.user_id = ?
        """, (doc_id, current_user["id"])).fetchone()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return dict(doc)


# ====== CHAT ENDPOINTS ======
@app.get("/api/profiles/{profile_id}/chats")
def list_chat_sessions(profile_id: int, profile=Depends(get_user_profile)):
    """Lấy danh sách phiên chat"""
    sessions = db.list_chat_sessions(profile_id)
    return sessions

@app.post("/api/profiles/{profile_id}/chats")
def create_chat_session(profile_id: int, profile=Depends(get_user_profile)):
    """Tạo phiên chat mới"""
    session_id = db.create_chat_session(profile_id)
    return {"message": "Tạo phiên chat thành công", "session_id": session_id}

@app.get("/api/chats/{session_id}/messages")
def get_chat_messages(session_id: int, current_user=Depends(get_current_user)):
    """Lấy tin nhắn trong phiên chat"""
    # Check ownership through profile
    with db.get_conn() as conn:
        session = conn.execute("""
            SELECT cs.*, hp.user_id
            FROM chat_sessions cs
            JOIN health_profiles hp ON cs.health_profile_id = hp.id
            WHERE cs.id = ? AND hp.user_id = ?
        """, (session_id, current_user["id"])).fetchone()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = db.list_chat_messages(session_id)
    return messages

@app.post("/api/chats/{session_id}/messages")
def send_chat_message(session_id: int, data: ChatMessageCreate, current_user=Depends(get_current_user)):
    """Gửi tin nhắn chat"""

    # Check ownership and get profile info
    with db.get_conn() as conn:
        session = conn.execute("""
            SELECT cs.*, hp.user_id, hp.conditions_text, hp.conditions_json, hp.weight, hp.height, hp.age, hp.gender
            FROM chat_sessions cs
            JOIN health_profiles hp ON cs.health_profile_id = hp.id
            WHERE cs.id = ? AND hp.user_id = ?
        """, (session_id, current_user["id"])).fetchone()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Extract profile_id from session
    profile_id = session["health_profile_id"]

    try:
        # Save user message with image data if present
        message_metadata = {}
        if data.image_data:
            message_metadata["has_image"] = True
            # Store base64 image in metadata for display
            message_metadata["image_data"] = data.image_data

        # Đánh dấu nếu là voice input
        if data.auto_play_response:
            message_metadata["voice_input"] = True

        # Save user message to database
        message_id = db.add_chat_message(session_id, "user", data.content, data.message_type, message_metadata)

        # --- TÍCH HỢP LANGCHAIN AGENT VÀ PINECONE ---

        # 1. Lấy dữ liệu hồ sơ cho AI context
        profile_data = dict(session)

        # 2. Lấy lịch sử chat từ Pinecone (nếu có) và DB
        chat_history_list = []
        if pinecone_db.pinecone_service.is_available():
            vector_store = pinecone_db.pinecone_service.get_vector_store()
            if vector_store:
                retriever = vector_store.as_retriever(search_kwargs={
                    'k': 5,
                    'filter': {
                        'user_id': current_user["id"],
                        'profile_id': profile_id,
                        'chat_id': session_id
                    }
                })
                # Lấy các document liên quan từ Pinecone bằng phương thức invoke mới
                context_docs = retriever.invoke(data.content)
                for doc in context_docs:
                    chat_history_list.append({"role": doc.metadata.get('role', 'user'), "content": doc.page_content})

        # Luôn lấy thêm các tin nhắn gần đây từ DB để đảm bảo luồng hội thoại
        db_messages = db.list_chat_messages(session_id, limit=6)
        # Tránh thêm trùng lặp
        seen_contents = {msg['content'] for msg in chat_history_list}
        for msg in reversed(db_messages):
            if msg['content'] not in seen_contents:
                chat_history_list.insert(0, {"role": msg["role"], "content": msg["content"]})

        # 3. Chuyển đổi lịch sử chat sang định dạng của LangChain
        langchain_chat_history = []
        for msg in chat_history_list:
            if msg["role"] == "user":
                langchain_chat_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_chat_history.append(AIMessage(content=msg["content"]))

        # 4. Tạo Agent Executor
        agent_executor = langchain_agent.create_chatbot_agent(
            user_id=current_user["id"],
            profile_id=profile_id,
            session_data=profile_data
        )

        # 5. Chuẩn bị input cho Agent
        agent_input = {"input": data.content, "chat_history": langchain_chat_history}
        if data.message_type == "image" and data.image_data:
            # Vision model support
            agent_input["input"] = [
                {"type": "text", "text": data.content or "Hãy phân tích thực phẩm trong ảnh này và tư vấn cho tôi."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data.image_data}"}}
            ]

        # 5. Gọi Agent để lấy phản hồi
        try:
            response = agent_executor.invoke(agent_input)
            ai_response = response.get("output", "Xin lỗi, tôi chưa thể trả lời câu hỏi này.")
        except Exception as e:
            logger.error(f"LangChain agent invocation error: {e}")
            ai_response = "Đã có lỗi xảy ra trong quá trình xử lý với AI. Vui lòng thử lại sau."

        # Save AI response to database
        ai_message_id = db.add_chat_message(session_id, "assistant", ai_response)

        # Save user and AI messages to Pinecone for future context
        if pinecone_db.pinecone_service.is_available():
            vector_store = pinecone_db.pinecone_service.get_vector_store()
            if vector_store:
                vector_store.add_texts(
                    texts=[data.content, ai_response],
                    metadatas=[
                        {
                            "role": "user",
                            "user_id": current_user["id"],
                            "profile_id": profile_id,
                            "chat_id": session_id
                        },
                        {
                            "role": "assistant",
                            "user_id": current_user["id"],
                            "profile_id": profile_id,
                            "chat_id": session_id
                        }
                    ],
                    ids=[f"msg_{message_id}", f"msg_{ai_message_id}"]
                )
                logger.info(f"Added user and AI messages to Pinecone: msg_{message_id}, msg_{ai_message_id}")

        # Tự động tạo audio nếu được yêu cầu
        audio_data_url = None
        if data.auto_play_response and tts.is_tts_available():
            try:
                audio_data_url = tts.generate_audio(ai_response)
                if audio_data_url:
                    logger.info("Auto-generated audio for AI response")
            except Exception as audio_error:
                logger.warning(f"Failed to generate auto-play audio: {audio_error}")

        return {
            "message": "Tin nhắn đã được gửi",
            "ai_response": ai_response,
            "auto_play_audio": audio_data_url
        }

    except Exception as e:
        import traceback
        logger.error(f"Error in send_chat_message: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý chat: {str(e)}")


# ====== TEXT-TO-SPEECH ======
class TTSRequest(BaseModel):
    text: str = Field(..., max_length=1000, description="Text to convert to speech")

@app.post("/api/tts/generate")
def generate_tts_audio(data: TTSRequest, current_user=Depends(get_current_user)):
    """Chuyển đổi text thành audio sử dụng Azure Speech Service Vietnamese"""

    if not tts.is_tts_available():
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Service chưa được cấu hình. Vui lòng thiết lập AZURE_SPEECH_KEY và cài đặt azure-cognitiveservices-speech"
        )

    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text không được để trống")

    try:
        # Sinh audio từ text
        audio_data_url = tts.generate_audio(data.text)

        if audio_data_url is None:
            raise HTTPException(
                status_code=500,
                detail="Không thể tạo audio. Vui lòng thử lại với text khác."
            )

        return {
            "success": True,
            "audio_data_url": audio_data_url,
            "text": data.text[:100] + "..." if len(data.text) > 100 else data.text
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tạo audio: {str(e)}"
        )

@app.post("/api/speech/recognize")
async def recognize_speech_audio(
    audio_file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    """Nhận diện giọng nói từ file audio thành text"""

    if not tts.is_speech_available():
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Service chưa được cấu hình. Vui lòng thiết lập AZURE_SPEECH_KEY"
        )

    # Kiểm tra file type
    if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File phải là định dạng audio")

    try:
        # Đọc audio data
        audio_data = await audio_file.read()

        # Nhận diện giọng nói
        recognized_text = tts.recognize_speech(audio_data)

        if recognized_text:
            return {
                "success": True,
                "text": recognized_text,
                "confidence": "high"  # Azure Speech Service thường có độ chính xác cao
            }
        else:
            return {
                "success": False,
                "text": "",
                "error": "Không thể nhận diện được giọng nói"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi nhận diện giọng nói: {str(e)}"
        )

@app.get("/api/speech/status")
def get_speech_status(current_user=Depends(get_current_user)):
    """Kiểm tra trạng thái của Azure Speech Service"""
    return {
        "available": tts.is_speech_available(),
        "service": "Azure Speech Service",
        "voice": "vi-VN-HoaiMyNeural",
        "supported_language": "Vietnamese",
        "features": {
            "text_to_speech": True,
            "speech_to_text": True
        },
        "format": "MP3",
        "available_voices": tts.azure_speech_service.get_available_voices() if tts.is_speech_available() else []
    }

# ====== MMS-TTS-VIE ENDPOINTS ======
@app.post("/api/mms-tts/generate")
def generate_mms_tts_audio(data: TTSRequest, current_user=Depends(get_current_user)):
    """Chuyển đổi text thành audio sử dụng Facebook MMS-TTS-VIE"""

    if not mms_tts.is_mms_tts_available():
        raise HTTPException(
            status_code=503,
            detail="Facebook MMS-TTS-VIE chưa được cấu hình. Vui lòng cài đặt transformers, torch, torchaudio"
        )

    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text không được để trống")

    try:
        # Sinh audio từ text
        audio_data_url = mms_tts.generate_audio_mms(data.text)

        if audio_data_url is None:
            raise HTTPException(
                status_code=500,
                detail="Không thể tạo audio. Vui lòng thử lại với text khác."
            )

        return {
            "success": True,
            "audio_data_url": audio_data_url,
            "text": data.text[:100] + "..." if len(data.text) > 100 else data.text,
            "service": "Facebook MMS-TTS-VIE"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tạo audio: {str(e)}"
        )

@app.get("/api/mms-tts/status")
def get_mms_tts_status(current_user=Depends(get_current_user)):
    """Kiểm tra trạng thái của Facebook MMS-TTS-VIE"""
    return {
        "available": mms_tts.is_mms_tts_available(),
        "service": "Facebook MMS-TTS-VIE",
        "model_id": "facebook/mms-tts-vie",
        "supported_language": "Vietnamese",
        "features": {
            "text_to_speech": True,
            "speech_to_text": False
        },
        "format": "WAV",
        "sample_rate": 24000,
        "model_info": mms_tts.mms_tts_service.get_model_info() if mms_tts.is_mms_tts_available() else None
    }



@app.get("/api/speech/token")
async def get_speech_token(current_user=Depends(get_current_user)):
    """Lấy token cho Azure Speech SDK frontend"""
    if not tts.is_speech_available():
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Service chưa được cấu hình"
        )

    try:
        # Azure Speech SDK cần subscription key để tạo token
        # Trong production, nên tạo token tạm thời qua Azure API
        return {
            "token": tts.azure_speech_service.speech_key,  # Temporary - should use proper token
            "region": tts.azure_speech_service.speech_region
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tạo token: {str(e)}"
        )

class SpeechRecognizeBase64Request(BaseModel):
    audio_data: str = Field(..., description="Base64 encoded audio data")
    mime_type: str = Field(default="audio/webm", description="MIME type of audio")

@app.post("/api/speech/recognize-base64")
async def recognize_speech_base64(
    request: SpeechRecognizeBase64Request,
    current_user=Depends(get_current_user)
):
    """Nhận diện giọng nói từ base64 audio data"""

    if not tts.is_speech_available():
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Service chưa được cấu hình. Vui lòng thiết lập AZURE_SPEECH_KEY"
        )

    audio_data = request.audio_data
    mime_type = request.mime_type

    try:
        # Decode base64 to bytes
        import base64
        audio_bytes = base64.b64decode(audio_data)

        # Nhận diện giọng nói
        recognized_text = tts.recognize_speech(audio_bytes)

        if recognized_text:
            return {
                "success": True,
                "text": recognized_text,
                "confidence": "high"
            }
        else:
            return {
                "success": False,
                "text": "",
                "error": "Không thể nhận diện được giọng nói"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi nhận diện giọng nói: {str(e)}"
        )

# Backward compatibility
@app.get("/api/tts/status")
def get_tts_status(current_user=Depends(get_current_user)):
    """Kiểm tra trạng thái của Azure Speech Service (backward compatibility)"""
    return get_speech_status(current_user)


# ====== ADMIN FOOD MANAGEMENT ======
@app.get("/api/foods")
def list_foods(
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user=Depends(get_current_user)
):
    """Lấy danh sách thực phẩm (cần đăng nhập)"""
    foods = db.list_foods(query, limit, offset)
    return foods

@app.get("/api/foods/{food_id}")
def get_food_detail(food_id: int, current_user=Depends(get_current_user)):
    """Lấy chi tiết thực phẩm"""
    food = db.get_food_by_id(food_id)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

@app.post("/api/foods")
def create_food_item(data: FoodCreate, admin_user=Depends(require_admin)):
    """Tạo thực phẩm mới (admin only)"""
    food_id = db.create_food(data.dict(), created_by=admin_user["id"])
    return {"message": "Tạo thực phẩm thành công", "food_id": food_id}

@app.put("/api/foods/{food_id}")
def update_food_item(food_id: int, data: FoodCreate, admin_user=Depends(require_admin)):
    """Cập nhật thực phẩm (admin only)"""
    success = db.update_food(food_id, data.dict(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Food not found")
    return {"message": "Cập nhật thực phẩm thành công"}

@app.delete("/api/foods/{food_id}")
def delete_food_item(food_id: int, admin_user=Depends(require_admin)):
    """Xóa thực phẩm (admin only)"""
    success = db.delete_food(food_id)
    if not success:
        raise HTTPException(status_code=404, detail="Food not found")
    return {"message": "Xóa thực phẩm thành công"}


# ====== STATISTICS ENDPOINTS ======
@app.get("/api/stats")
def get_system_stats(admin_user=Depends(require_admin)):
    """Lấy thống kê hệ thống (admin only)"""
    return db.get_stats()

@app.get("/api/me/stats")
def get_my_stats(current_user=Depends(get_current_user)):
    """Lấy thống kê cá nhân"""
    return db.get_user_stats(current_user["id"])


# ====== HEALTH PLANNING ENDPOINTS ======

@app.get("/api/profiles/{profile_id}/health-plans")
def list_health_plans(profile_id: int, status: Optional[str] = None, profile=Depends(get_user_profile)):
    """Lấy danh sách kế hoạch sức khỏe"""
    plans = db.get_health_plans(profile_id, status)
    return plans

@app.post("/api/profiles/{profile_id}/health-plans")
def create_health_plan(profile_id: int, data: HealthPlanCreate, profile=Depends(get_user_profile)):
    """Tạo kế hoạch sức khỏe mới"""
    try:
        # Lấy thông tin profile để truyền cho AI
        profile_data = dict(profile)
        
        # Tạo kế hoạch với AI
        plan_id, ai_analysis = health_planner.health_planner_service.create_health_plan(
            health_profile_id=profile_id,
            title=data.title,
            goal_type=data.goal_type.value,
            target_value=data.target_value,
            target_unit=data.target_unit,
            duration_days=data.duration_days,
            start_date=data.start_date,
            available_activities=data.available_activities,
            dietary_restrictions=data.dietary_restrictions,
            profile_data=profile_data
        )
        
        return {
            "message": "Tạo kế hoạch thành công",
            "plan_id": plan_id,
            "ai_analysis": ai_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo kế hoạch: {str(e)}")

@app.get("/api/profiles/{profile_id}/health-plans/{plan_id}")
def get_health_plan_detail(profile_id: int, plan_id: int, profile=Depends(get_user_profile)):
    """Lấy chi tiết kế hoạch sức khỏe"""
    plan = db.get_health_plan(plan_id, profile_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Kế hoạch không tìm thấy")
    return plan

@app.put("/api/profiles/{profile_id}/health-plans/{plan_id}")
def update_health_plan(profile_id: int, plan_id: int, data: HealthPlanUpdate, profile=Depends(get_user_profile)):
    """Cập nhật kế hoạch sức khỏe"""
    updates = data.dict(exclude_unset=True)
    success = db.update_health_plan(plan_id, profile_id, **updates)
    if not success:
        raise HTTPException(status_code=404, detail="Kế hoạch không tìm thấy")
    return {"message": "Cập nhật kế hoạch thành công"}

@app.delete("/api/profiles/{profile_id}/health-plans/{plan_id}")
def delete_health_plan(profile_id: int, plan_id: int, profile=Depends(get_user_profile)):
    """Xóa kế hoạch sức khỏe"""
    success = db.delete_health_plan(plan_id, profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Kế hoạch không tìm thấy")
    return {"message": "Xóa kế hoạch thành công"}

# ====== DAILY PLAN & ACTIVITIES ======

@app.get("/api/health-plans/{plan_id}/daily/{date}")
def get_daily_plan(plan_id: int, date: str, current_user=Depends(get_current_user)):
    """Lấy kế hoạch hàng ngày"""
    # Verify ownership
    with db.get_conn() as conn:
        plan = conn.execute(
            """
            SELECT hp.* FROM health_plans hp
            JOIN health_profiles hpr ON hp.health_profile_id = hpr.id
            WHERE hp.id = ? AND hpr.user_id = ?
            """,
            (plan_id, current_user["id"])
        ).fetchone()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Kế hoạch không tìm thấy")
    
    summary = db.get_daily_plan_summary(plan_id, date)
    return summary

@app.get("/api/health-plans/{plan_id}/activities")
def get_plan_activities(plan_id: int, date: Optional[str] = None, current_user=Depends(get_current_user)):
    """Lấy hoạt động trong kế hoạch"""
    # Verify ownership
    with db.get_conn() as conn:
        plan = conn.execute(
            """
            SELECT hp.* FROM health_plans hp
            JOIN health_profiles hpr ON hp.health_profile_id = hpr.id
            WHERE hp.id = ? AND hpr.user_id = ?
            """,
            (plan_id, current_user["id"])
        ).fetchone()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Kế hoạch không tìm thấy")
    
    activities = db.get_plan_activities(plan_id, date)
    return activities

@app.put("/api/health-plans/{plan_id}/activities/{activity_id}")
def update_plan_activity_endpoint(
    plan_id: int,
    activity_id: int,
    data: ActivityUpdate,
    current_user=Depends(get_current_user)
):
    """Cập nhật hoạt động trong kế hoạch (đổi bộ môn, thời lượng, cường độ, ...)."""
    # Verify ownership
    with db.get_conn() as conn:
        activity = conn.execute(
            """
            SELECT hpa.* FROM health_plan_activities hpa
            JOIN health_plans hp ON hpa.health_plan_id = hp.id
            JOIN health_profiles hpr ON hp.health_profile_id = hpr.id
            WHERE hpa.id = ? AND hp.id = ? AND hpr.user_id = ?
            """,
            (activity_id, plan_id, current_user["id"])
        ).fetchone()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Hoạt động không tìm thấy")

    ok = db.update_plan_activity(
        activity_id=activity_id,
        activity_type=data.activity_type,
        activity_name=data.activity_name,
        duration_minutes=data.duration_minutes,
        intensity=data.intensity.value if getattr(data, 'intensity', None) else None,
        calories_target=data.calories_target,
        instructions=data.instructions
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Không có thay đổi để cập nhật")
    return {"message": "Cập nhật hoạt động thành công"}

@app.post("/api/health-plans/{plan_id}/activities/{activity_id}/complete")
def complete_activity(
    plan_id: int, 
    activity_id: int, 
    actual_duration: int,
    actual_intensity: str,
    notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Hoàn thành hoạt động"""
    # Verify ownership
    with db.get_conn() as conn:
        activity = conn.execute(
            """
            SELECT hpa.* FROM health_plan_activities hpa
            JOIN health_plans hp ON hpa.health_plan_id = hp.id
            JOIN health_profiles hpr ON hp.health_profile_id = hpr.id
            WHERE hpa.id = ? AND hp.id = ? AND hpr.user_id = ?
            """,
            (activity_id, plan_id, current_user["id"])
        ).fetchone()
    
    if not activity:
        raise HTTPException(status_code=404, detail="Hoạt động không tìm thấy")
    
    success = db.complete_plan_activity(activity_id, actual_duration, actual_intensity, notes)
    if not success:
        raise HTTPException(status_code=400, detail="Không thể hoàn thành hoạt động")
    
    return {"message": "Hoàn thành hoạt động thành công"}

@app.get("/api/health-plans/{plan_id}/meals")
def get_plan_meals(plan_id: int, date: Optional[str] = None, current_user=Depends(get_current_user)):
    """Lấy bữa ăn trong kế hoạch"""
    # Verify ownership
    with db.get_conn() as conn:
        plan = conn.execute(
            """
            SELECT hp.* FROM health_plans hp
            JOIN health_profiles hpr ON hp.health_profile_id = hpr.id
            WHERE hp.id = ? AND hpr.user_id = ?
            """,
            (plan_id, current_user["id"])
        ).fetchone()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Kế hoạch không tìm thấy")
    
    meals = db.get_plan_meals(plan_id, date)
    return meals

@app.post("/api/health-plans/{plan_id}/meals/{meal_id}/complete")
def complete_meal(
    plan_id: int,
    meal_id: int,
    actual_foods: List[Dict[str, Any]],
    deviation_notes: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Hoàn thành bữa ăn"""
    # Verify ownership
    with db.get_conn() as conn:
        meal = conn.execute(
            """
            SELECT hpm.* FROM health_plan_meals hpm
            JOIN health_plans hp ON hpm.health_plan_id = hp.id
            JOIN health_profiles hpr ON hp.health_profile_id = hpr.id
            WHERE hpm.id = ? AND hp.id = ? AND hpr.user_id = ?
            """,
            (meal_id, plan_id, current_user["id"])
        ).fetchone()
    
    if not meal:
        raise HTTPException(status_code=404, detail="Bữa ăn không tìm thấy")
    
    success = db.complete_plan_meal(meal_id, actual_foods, deviation_notes)
    if not success:
        raise HTTPException(status_code=400, detail="Không thể hoàn thành bữa ăn")
    
    return {"message": "Hoàn thành bữa ăn thành công"}

# ====== ACTIVITY & MEAL LOGGING ======

@app.post("/api/profiles/{profile_id}/activity-logs")
def log_activity(profile_id: int, data: ActivityLog, profile=Depends(get_user_profile)):
    """Ghi nhận hoạt động thực hiện"""
    log_id = db.log_activity(
        health_profile_id=profile_id,
        date=data.date.isoformat(),
        activity_type=data.activity_type,
        activity_name=data.activity_name,
        duration_minutes=data.duration_minutes,
        intensity=data.intensity.value,
        calories_burned=data.calories_burned,
        notes=data.notes,
        source=data.source,
        activity_plan_id=data.activity_plan_id
    )
    return {"message": "Ghi nhận hoạt động thành công", "log_id": log_id}

@app.post("/api/profiles/{profile_id}/meal-logs")
def log_meal(profile_id: int, data: MealLog, profile=Depends(get_user_profile)):
    """Ghi nhận bữa ăn thực hiện"""
    log_id = db.log_meal(
        health_profile_id=profile_id,
        date=data.date.isoformat(),
        meal_type=data.meal_type.value,
        food_items=data.food_items,
        total_calories=data.total_calories,
        notes=data.notes,
        source=data.source,
        meal_plan_id=data.meal_plan_id
    )
    return {"message": "Ghi nhận bữa ăn thành công", "log_id": log_id}

@app.get("/api/profiles/{profile_id}/activity-logs")
def get_activity_logs(profile_id: int, date: Optional[str] = None, limit: int = 50, profile=Depends(get_user_profile)):
    """Lấy lịch sử hoạt động"""
    logs = db.get_activity_logs(profile_id, date, limit)
    return logs

@app.get("/api/profiles/{profile_id}/meal-logs")
def get_meal_logs(profile_id: int, date: Optional[str] = None, limit: int = 50, profile=Depends(get_user_profile)):
    """Lấy lịch sử bữa ăn"""
    logs = db.get_meal_logs(profile_id, date, limit)
    return logs

# ====== PLAN ADJUSTMENT ======

class PlanAdjustmentRequest(BaseModel):
    """Yêu cầu điều chỉnh kế hoạch"""
    target_date: str = Field(..., description="Ngày bắt đầu điều chỉnh (YYYY-MM-DD)")
    adjustment_days: int = Field(default=7, ge=1, le=30, description="Số ngày điều chỉnh")
    reason: Optional[str] = Field(None, description="Lý do điều chỉnh")

@app.post("/api/profiles/{profile_id}/health-plans/{plan_id}/adjust")
def adjust_health_plan(
    profile_id: int,
    plan_id: int,
    data: PlanAdjustmentRequest,
    profile=Depends(get_user_profile)
):
    """Tự động điều chỉnh kế hoạch dựa trên hoạt động thực tế"""
    try:
        from datetime import datetime
        
        # Parse target date
        target_date = datetime.fromisoformat(data.target_date).date()
        
        # Lấy hoạt động và bữa ăn gần đây
        recent_activities = db.get_activity_logs(profile_id, limit=20)
        recent_meals = db.get_meal_logs(profile_id, limit=20)
        
        # Điều chỉnh kế hoạch với AI
        result = health_planner.health_planner_service.adjust_plan_based_on_feedback(
            plan_id=plan_id,
            health_profile_id=profile_id,
            actual_activities=recent_activities,
            actual_meals=recent_meals,
            target_date=target_date,
            adjustment_days=data.adjustment_days
        )
        
        return {
            "message": "Điều chỉnh kế hoạch thành công",
            "adjustment_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi điều chỉnh kế hoạch: {str(e)}")


# ====== ERROR HANDLERS ======
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "API endpoint not found"}, status_code=404)
    # Fallback to serve frontend for non-API routes
    try:
        with open("app/frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except Exception:
        return HTMLResponse("Not Found", status_code=404)

# Mount static files sau khi định nghĩa tất cả API, để tránh che route /api/*
app.mount("/", StaticFiles(directory="app/frontend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)