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
from passlib.context import CryptContext

from .services import db
from .services import pdf as pdfsvc
from .services import azure_openai as llm
from .services import food_tools
from .services import tts

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
            
        db.add_chat_message(session_id, "user", data.content, data.message_type, message_metadata)
        
        # Get profile data for AI context
        # sqlite3.Row không hỗ trợ get(); dùng key access trực tiếp
        profile_data = {
            "profile_name": (session["session_name"] if "session_name" in session.keys() else "Người dùng"),
            "conditions_text": (session["conditions_text"] if "conditions_text" in session.keys() else None),
            "conditions_json": (session["conditions_json"] if "conditions_json" in session.keys() else None),
            "weight": (session["weight"] if "weight" in session.keys() else None),
            "height": (session["height"] if "height" in session.keys() else None),
            "age": (session["age"] if "age" in session.keys() else None),
            "gender": (session["gender"] if "gender" in session.keys() else None),
        }
        
        # Get recent chat history for context (use stored role)
        recent_messages = db.list_chat_messages(session_id, limit=10)
        chat_history: List[Dict[str, str]] = []
        for msg in recent_messages:
            msg_role = msg["role"] if "role" in msg.keys() else "user"
            chat_history.append({"role": msg_role, "content": msg["content"]})
        
        # Define tool executor function
        def tool_executor(name: str, args: dict):
            if name == "search_food_database":
                food_name = args.get("food_name", "")
                foods = db.search_food_by_name(food_name)
                if foods:
                    food = foods[0]
                    # Chuẩn hóa schema trả về để LLM sử dụng
                    return {
                        "name": food["name"] if "name" in food.keys() else "",
                        "category": food["category"] if "category" in food.keys() else "",
                        "nutrients": food["nutrients"] if "nutrients" in food.keys() else {},
                        "contraindications": food["contraindications"] if "contraindications" in food.keys() else [],
                        "recommended_portions": food["recommended_portions"] if "recommended_portions" in food.keys() else {},
                        "preparation_notes": food["preparation_notes"] if "preparation_notes" in food.keys() else "",
                    }
                return {"error": f"Không tìm thấy thông tin về {food_name}"}
            
            elif name == "update_health_status":
                new_conditions = args.get("new_conditions", [])
                condition_text_update = args.get("condition_text_update", "")
                weight_delta = args.get("weight_delta_kg")
                new_weight = args.get("new_weight_kg")
                new_height = args.get("new_height_cm")
                age = args.get("age")
                gender = args.get("gender")
                
                # Get current conditions from session data
                current_conditions = (session["conditions_json"] if "conditions_json" in session.keys() else "{}")
                if isinstance(current_conditions, str):
                    try:
                        conditions_data = json.loads(current_conditions)
                        # Ensure it's a dictionary
                        if not isinstance(conditions_data, dict):
                            conditions_data = {"conditions_list": []}
                    except Exception:
                        conditions_data = {"conditions_list": []}
                else:
                    conditions_data = current_conditions or {"conditions_list": []}
                
                # Ensure conditions_data is a dict before using .get()
                if not isinstance(conditions_data, dict):
                    conditions_data = {"conditions_list": []}
                
                # Merge new conditions
                existing_conditions = conditions_data.get("conditions_list", [])
                for condition in new_conditions:
                    if condition and condition not in existing_conditions:
                        existing_conditions.append(condition)
                conditions_data["conditions_list"] = existing_conditions
                
                # Build updates
                update_data: Dict[str, Any] = {
                    "conditions_json": json.dumps(conditions_data, ensure_ascii=False)
                }
                
                # Update condition text
                if condition_text_update:
                    current_text = (session["conditions_text"] if "conditions_text" in session.keys() else "")
                    update_data["conditions_text"] = (f"{current_text}\n{condition_text_update}" if current_text else condition_text_update)
                
                # Update age
                if age is not None:
                    try:
                        update_data["age"] = int(age)
                    except Exception:
                        pass
                
                # Update gender (map Vietnamese to English)
                if gender:
                    gender_mapping = {
                        "Nam": "male",
                        "Nữ": "female", 
                        "Khác": "other",
                        "male": "male",
                        "female": "female",
                        "other": "other"
                    }
                    mapped_gender = gender_mapping.get(gender)
                    if mapped_gender:
                        update_data["gender"] = mapped_gender
                
                # Update height
                if new_height is not None:
                    try:
                        update_data["height"] = float(new_height)
                    except Exception:
                        pass
                
                # Weight update
                current_weight = None
                try:
                    current_weight = float(session["weight"]) if session["weight"] is not None else None
                except Exception:
                    current_weight = None
                if new_weight is not None:
                    try:
                        update_data["weight"] = float(new_weight)
                    except Exception:
                        pass
                elif weight_delta is not None and current_weight is not None:
                    try:
                        update_data["weight"] = float(current_weight) + float(weight_delta)
                    except Exception:
                        pass
                
                # Apply update
                profile_id = session["health_profile_id"]
                db.update_health_profile(profile_id, current_user["id"], **update_data)
                
                return {
                    "success": True,
                    "updated_conditions": existing_conditions,
                    "updated_weight": update_data.get("weight", current_weight),
                    "updated_height": update_data.get("height"),
                    "updated_age": update_data.get("age"),
                    "updated_gender": update_data.get("gender"),
                    "message": "Đã cập nhật tình trạng sức khỏe thành công"
                }
            
            return {"error": f"Không tìm thấy function {name}"}
        
        # Define available tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_food_database",
                    "description": "Tra cứu thông tin chi tiết về thực phẩm trong cơ sở dữ liệu",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "food_name": {
                                "type": "string",
                                "description": "Tên thực phẩm cần tra cứu"
                            }
                        },
                        "required": ["food_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_health_status",
                    "description": "Cập nhật hồ sơ sức khỏe khi người dùng chia sẻ thông tin về tuổi, cân nặng, chiều cao, tình trạng bệnh lý",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "new_conditions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Danh sách bệnh lý/tình trạng mới (ví dụ: 'tiểu đường', 'cao huyết áp', 'dị ứng tôm cua')"
                            },
                            "condition_text_update": {
                                "type": "string",
                                "description": "Ghi chú chi tiết về tình trạng sức khỏe (ví dụ: 'Mới phát hiện tiểu đường type 2', 'Bị dị ứng hải sản')"
                            },
                            "age": {
                                "type": "integer",
                                "description": "Tuổi của người dùng (ví dụ: 25, 45)"
                            },
                            "gender": {
                                "type": "string",
                                "enum": ["Nam", "Nữ", "Khác"],
                                "description": "Giới tính (sử dụng tiếng Việt: Nam, Nữ, Khác)"
                            },
                            "weight_delta_kg": {
                                "type": "number",
                                "description": "Mức thay đổi cân nặng theo kg (+2 = tăng 2kg, -1.5 = giảm 1.5kg)"
                            },
                            "new_weight_kg": {
                                "type": "number",
                                "description": "Cân nặng hiện tại theo kg (ví dụ: 65.5)"
                            },
                            "new_height_cm": {
                                "type": "number",
                                "description": "Chiều cao theo cm (ví dụ: 170)"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]
        
        # Build system message with profile context
        profile_context = f"""
THÔNG TIN NGƯỜI DÙNG:
- Hồ sơ: {profile_data.get('profile_name', 'Không rõ')}
- Tuổi: {profile_data.get('age', 'chưa có')}
- Giới tính: {profile_data.get('gender', 'chưa có')}
- Cân nặng hiện tại: {profile_data.get('weight', 'chưa có')} kg
- Chiều cao: {profile_data.get('height', 'chưa có')} cm
- Tình trạng sức khỏe: {profile_data.get('conditions_text', 'Chưa có thông tin')}
"""
        
        # Parse conditions_json for specific conditions
        conditions_json = profile_data.get('conditions_json', '{}')
        if isinstance(conditions_json, str):
            try:
                conditions_data = json.loads(conditions_json)
                if conditions_data.get('conditions_list'):
                    profile_context += f"- Bệnh lý cụ thể: {', '.join(conditions_data['conditions_list'])}\n"
            except:
                pass
        
        system_message = {
            "role": "system",
            "content": f"""Bạn là chuyên gia tư vấn sức khỏe và dinh dưỡng. Nhiệm vụ của bạn:

1. TƯ VẤN THỰC PHẨM: 
   - Sử dụng kiến thức chuyên môn của bạn để tư vấn về thực phẩm
   - Đưa ra lời khuyên dựa trên tình trạng sức khỏe cụ thể của người dùng
   - Chỉ sử dụng function search_food_database khi gặp thực phẩm đặc thù/địa phương mà bạn không chắc chắn
   - Đánh giá: có nên ăn, lượng bao nhiêu, cách chế biến phù hợp

2. CẬP NHẬT THÔNG TIN SỨC KHỎE:
   - QUAN TRỌNG: Khi người dùng chia sẻ bất kỳ thông tin cá nhân nào về sức khỏe, hãy LUÔN gọi function update_health_status
   - Các trường hợp cần cập nhật:
     * Tuổi: "Tôi 25 tuổi", "Năm nay tôi 30"
     * Giới tính: "Tôi là nam/nữ"
     * Cân nặng: "Tôi nặng 65kg", "Tôi tăng 2kg", "Giảm được 3kg"
     * Chiều cao: "Cao 1m70", "Tôi cao 165cm"
     * Bệnh lý: "Tôi bị tiểu đường", "Mắc cao huyết áp", "Dị ứng hải sản"
   - Ví dụ function calls:
     * "Tôi 28 tuổi, cao 1m75, nặng 70kg" -> update_health_status({{"age": 28, "new_height_cm": 175, "new_weight_kg": 70}})
     * "Tôi bị tiểu đường type 2" -> update_health_status({{"new_conditions": ["tiểu đường type 2"], "condition_text_update": "Mắc tiểu đường type 2"}})
     * "Tăng 3kg trong 2 tháng" -> update_health_status({{"weight_delta_kg": 3, "condition_text_update": "Tăng 3kg trong 2 tháng"}})

3. NGUYÊN TẮC TƯ VẤN:
   - Ưu tiên an toàn sức khỏe
   - Đưa ra lời khuyên cụ thể, thực tế
   - Khuyến nghị tham khảo bác sĩ khi cần thiết
   - Luôn cập nhật thông tin hồ sơ khi có dữ liệu mới

{profile_context}

Hãy trả lời một cách chuyên nghiệp, thân thiện và dựa trên bằng chứng khoa học."""
        }
        
        # Build messages
        messages = [system_message]
        messages.extend(chat_history[-6:])  # Keep last 6 messages for context
        
        # Build user message with optional image
        user_message = {"role": "user", "content": []}
        
        if data.message_type == "image" and data.image_data:
            # Image message with vision
            user_message["content"] = [
                {"type": "text", "text": data.content or "Hãy phân tích thực phẩm trong ảnh này và tư vấn cho tôi."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data.image_data}"}}
            ]
        else:
            # Text-only message
            user_message["content"] = data.content
            
        messages.append(user_message)
        
        # Get AI response with function calling (dùng alias llm đã import)
        try:
            ai_response = llm.chat_with_food_tools(messages, tools, tool_executor)
        except Exception as ai_err:
            # Fallback khi Azure OpenAI chưa cấu hình hoặc lỗi mạng
            print(f"AI fallback due to error: {ai_err}")
            cond_text = profile_data.get('conditions_text') or 'chưa có thông tin cụ thể'
            ai_response = (
                "Hiện chưa kết nối được dịch vụ AI. Tôi đưa ra tư vấn cơ bản dựa trên thông tin hồ sơ hiện tại.\n"
                f"- Tình trạng sức khỏe: {cond_text}.\n"
                "- Với câu hỏi thực phẩm, bạn nên ưu tiên ăn đa dạng, nhiều rau xanh, hạn chế đường tinh luyện và đồ chiên rán.\n"
                "- Khi có bệnh lý mạn tính (ví dụ tiểu đường, tăng huyết áp), cần tham khảo bác sĩ trước khi thay đổi chế độ ăn.\n"
                "Vui lòng cấu hình AZURE_OPENAI_ENDPOINT và AZURE_OPENAI_API_KEY để nhận tư vấn chi tiết hơn."
            )
        
        # Save AI response
        db.add_chat_message(session_id, "assistant", ai_response)
        
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