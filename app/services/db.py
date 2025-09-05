import csv
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "chatgpu.db"))
SCHEMA_VERSION = 3


def _now() -> str:
    return datetime.utcnow().isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def _get_schema_version(conn: sqlite3.Connection) -> int:
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meta'")
        if not cur.fetchone():
            return 0
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
        (str(version),),
    )


def init_db(seed: bool = True) -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        cur = conn.cursor()

        # Nếu schema cũ hoặc chưa có, làm sạch và tạo mới
        current_version = _get_schema_version(conn)
        if current_version != SCHEMA_VERSION:
            # Drop tất cả bảng có thể có từ schema cũ/mới để tránh xung đột
            tables_to_drop = [
                "chat_messages",
                "chat_sessions",
                "documents",
                "health_profiles",
                "health_plans",
                "health_plan_activities",
                "health_plan_meals",
                "activity_logs",
                "meal_logs",
                "foods",
                "user_sessions",
                "users",
                "profiles",
                "accounts",
                "chats",
                "meta",
            ]
            for t in tables_to_drop:
                try:
                    cur.execute(f"DROP TABLE IF EXISTS {t};")
                except Exception:
                    pass

        # 1. USERS - Main user accounts (simplified)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              full_name TEXT NOT NULL,
              role TEXT DEFAULT 'user',
              is_active BOOLEAN DEFAULT 1,
              last_login_at TEXT,
              created_at TEXT,
              updated_at TEXT
            );
            """
        )
        
        # 2. HEALTH_PROFILES - Hồ sơ sức khỏe (1 user có nhiều profiles)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS health_profiles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              profile_name TEXT NOT NULL,
              age INTEGER,
              gender TEXT CHECK(gender IN ('male', 'female', 'other')),
              weight REAL,
              height REAL,
              conditions_text TEXT,
              conditions_json TEXT,
              is_default BOOLEAN DEFAULT 0,
              created_at TEXT,
              updated_at TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
              UNIQUE(user_id, profile_name)
            );
            """
        )
        
        # 3. DOCUMENTS - Tài liệu y tế theo profile
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_profile_id INTEGER NOT NULL,
              filename TEXT NOT NULL,
              original_content TEXT,
              ai_summary TEXT,
              file_type TEXT DEFAULT 'pdf',
              file_size INTEGER,
              uploaded_at TEXT,
              FOREIGN KEY(health_profile_id) REFERENCES health_profiles(id) ON DELETE CASCADE
            );
            """
        )
        
        # 4. CHAT_SESSIONS - Phiên chat theo profile
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_profile_id INTEGER NOT NULL,
              session_name TEXT,
              started_at TEXT,
              last_message_at TEXT,
              FOREIGN KEY(health_profile_id) REFERENCES health_profiles(id) ON DELETE CASCADE
            );
            """
        )
        
        # 5. CHAT_MESSAGES - Tin nhắn trong session
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER NOT NULL,
              role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
              content TEXT NOT NULL,
              message_type TEXT DEFAULT 'text' CHECK(message_type IN ('text', 'image', 'file')),
              metadata_json TEXT,
              created_at TEXT,
              FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );
            """
        )
        
        # 6. FOODS - Database thực phẩm (cải tiến)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS foods (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT UNIQUE NOT NULL,
              category TEXT,
              subcategory TEXT,
              nutrients_json TEXT,
              contraindications_json TEXT,
              benefits_json TEXT,
              recommended_portions_json TEXT,
              preparation_notes TEXT,
              source_reliability TEXT DEFAULT 'verified',
              created_by INTEGER,
              created_at TEXT,
              updated_at TEXT,
              FOREIGN KEY(created_by) REFERENCES users(id)
            );
            """
        )
        
        # 7. USER_SESSIONS - Tracking đăng nhập
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL,
              device_info TEXT,
              ip_address TEXT,
              expires_at TEXT,
              created_at TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        
        # 8. HEALTH_PLANS - Kế hoạch sức khỏe
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS health_plans (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_profile_id INTEGER NOT NULL,
              title TEXT NOT NULL,
              goal_type TEXT CHECK(goal_type IN ('weight_gain', 'weight_loss', 'muscle_gain', 'endurance', 'recovery', 'maintenance')) NOT NULL,
              target_value REAL,  -- Mục tiêu (kg, %, etc.)
              target_unit TEXT,   -- Đơn vị (kg, %, days)
              duration_days INTEGER NOT NULL,  -- Thời gian (ngày)
              start_date TEXT NOT NULL,
              end_date TEXT NOT NULL,
              current_progress REAL DEFAULT 0,
              status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'cancelled')),
              available_activities_json TEXT,  -- Hoạt động người dùng có thể thực hiện
              dietary_restrictions_json TEXT,  -- Hạn chế ăn uống
              ai_analysis_json TEXT,  -- Phân tích AI ban đầu
              created_at TEXT,
              updated_at TEXT,
              FOREIGN KEY(health_profile_id) REFERENCES health_profiles(id) ON DELETE CASCADE
            );
            """
        )
        
        # 9. HEALTH_PLAN_ACTIVITIES - Hoạt động tập luyện trong kế hoạch
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS health_plan_activities (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_plan_id INTEGER NOT NULL,
              date TEXT NOT NULL,  -- Ngày thực hiện (YYYY-MM-DD)
              activity_type TEXT NOT NULL,  -- swimming, football, gym, etc.
              activity_name TEXT NOT NULL,
              duration_minutes INTEGER,
              intensity TEXT CHECK(intensity IN ('low', 'medium', 'high')),
              calories_target REAL,
              instructions TEXT,
              is_completed BOOLEAN DEFAULT 0,
              completed_at TEXT,
              actual_duration_minutes INTEGER,
              actual_intensity TEXT,
              notes TEXT,
              created_at TEXT,
              FOREIGN KEY(health_plan_id) REFERENCES health_plans(id) ON DELETE CASCADE
            );
            """
        )
        
        # 10. HEALTH_PLAN_MEALS - Bữa ăn trong kế hoạch
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS health_plan_meals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_plan_id INTEGER NOT NULL,
              date TEXT NOT NULL,  -- Ngày ăn (YYYY-MM-DD)
              meal_type TEXT CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')) NOT NULL,
              food_items_json TEXT,  -- Danh sách thực phẩm
              total_calories REAL,
              macros_json TEXT,  -- protein, carbs, fat
              preparation_notes TEXT,
              is_completed BOOLEAN DEFAULT 0,
              completed_at TEXT,
              actual_foods_json TEXT,  -- Thực phẩm thực tế đã ăn
              deviation_notes TEXT,  -- Ghi chú về sự khác biệt
              created_at TEXT,
              FOREIGN KEY(health_plan_id) REFERENCES health_plans(id) ON DELETE CASCADE
            );
            """
        )
        
        # 11. ACTIVITY_LOGS - Lịch sử hoạt động thực tế
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_profile_id INTEGER NOT NULL,
              activity_plan_id INTEGER,  -- Link tới kế hoạch (nếu có)
              date TEXT NOT NULL,
              activity_type TEXT NOT NULL,
              activity_name TEXT NOT NULL,
              duration_minutes INTEGER,
              intensity TEXT,
              calories_burned REAL,
              notes TEXT,
              source TEXT DEFAULT 'manual',  -- manual, chat, auto
              logged_at TEXT,
              FOREIGN KEY(health_profile_id) REFERENCES health_profiles(id) ON DELETE CASCADE,
              FOREIGN KEY(activity_plan_id) REFERENCES health_plan_activities(id)
            );
            """
        )
        
        # 12. MEAL_LOGS - Lịch sử bữa ăn thực tế
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meal_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              health_profile_id INTEGER NOT NULL,
              meal_plan_id INTEGER,  -- Link tới kế hoạch (nếu có)
              date TEXT NOT NULL,
              meal_type TEXT NOT NULL,
              food_items_json TEXT,
              total_calories REAL,
              notes TEXT,
              source TEXT DEFAULT 'manual',  -- manual, chat, auto
              logged_at TEXT,
              FOREIGN KEY(health_profile_id) REFERENCES health_profiles(id) ON DELETE CASCADE,
              FOREIGN KEY(meal_plan_id) REFERENCES health_plan_meals(id)
            );
            """
        )
        
        # Indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_health_profiles_user ON health_profiles(user_id);")
        
        # Health planning indexes
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_health_plans_profile ON health_plans(health_profile_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_health_plans_dates ON health_plans(start_date, end_date);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_plan_activities_plan_date ON health_plan_activities(health_plan_id, date);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_plan_meals_plan_date ON health_plan_meals(health_plan_id, date);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_profile_date ON activity_logs(health_profile_id, date);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meal_logs_profile_date ON meal_logs(health_profile_id, date);")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_profile ON documents(health_profile_id);")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_profile ON chat_sessions(health_profile_id);")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);")
        except sqlite3.OperationalError:
            pass
        cur.execute("CREATE INDEX IF NOT EXISTS idx_foods_category ON foods(category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token_hash);")
        
        # Ghi version
        _set_schema_version(conn, SCHEMA_VERSION)

    if seed:
        seed_foods_from_csv()


def seed_foods_from_csv() -> None:
    seed_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "seed_food.csv"))
    if not os.path.exists(seed_path):
        return
    with get_conn() as conn, open(seed_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO foods(name, category, nutrients_json, contraindications_text, recommended_portion, notes) VALUES (?,?,?,?,?,?)",
                    (
                        name,
                        row.get("category"),
                        json.dumps(json.loads(row.get("nutrients_json" or "{}")), ensure_ascii=False),
                        row.get("contraindications_text"),
                        row.get("recommended_portion"),
                        row.get("notes"),
                    ),
                )
            except Exception:
                # cố gắng insert nhẹ nhàng, bỏ qua lỗi CSV
                continue


# ====== USER MANAGEMENT ======
def create_user(email: str, password_hash: str, full_name: str, role: str = 'user') -> int:
    """Tạo user mới"""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users(email, password_hash, full_name, role, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (email.lower().strip(), password_hash, full_name, role, _now(), _now()),
        )
        return int(cur.lastrowid)


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    """Lấy user theo email"""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower().strip(),))
        return cur.fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    """Lấy user theo ID"""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,))
        return cur.fetchone()


def update_user_login(user_id: int) -> None:
    """Cập nhật thời gian đăng nhập cuối"""
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (_now(), _now(), user_id))


# ====== HEALTH PROFILES MANAGEMENT ======
def create_health_profile(user_id: int, profile_name: str, age: Optional[int] = None, 
                         gender: Optional[str] = None, weight: Optional[float] = None, 
                         height: Optional[float] = None, conditions_text: str = "", 
                         conditions_json: Optional[Dict[str, Any]] = None, 
                         is_default: bool = False) -> int:
    """Tạo hồ sơ sức khỏe mới"""
    with get_conn() as conn:
        # Nếu set là default, unset tất cả profiles khác của user
        if is_default:
            conn.execute("UPDATE health_profiles SET is_default = 0 WHERE user_id = ?", (user_id,))
        
        cur = conn.execute(
            """INSERT INTO health_profiles(user_id, profile_name, age, gender, weight, height, 
               conditions_text, conditions_json, is_default, created_at, updated_at) 
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id, profile_name, age, gender, weight, height, conditions_text, 
             json.dumps(conditions_json or {}, ensure_ascii=False), is_default, _now(), _now()),
        )
        return int(cur.lastrowid)


def list_health_profiles(user_id: int) -> List[sqlite3.Row]:
    """Lấy danh sách hồ sơ sức khỏe của user"""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM health_profiles WHERE user_id=? ORDER BY is_default DESC, updated_at DESC", 
            (user_id,)
        )
        return cur.fetchall()


def get_health_profile(profile_id: int, user_id: int) -> Optional[sqlite3.Row]:
    """Lấy hồ sơ sức khỏe theo ID (với ownership check)"""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM health_profiles WHERE id=? AND user_id=?", (profile_id, user_id))
        return cur.fetchone()


def get_default_health_profile(user_id: int) -> Optional[sqlite3.Row]:
    """Lấy hồ sơ sức khỏe mặc định của user"""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM health_profiles WHERE user_id=? AND is_default=1", (user_id,))
        profile = cur.fetchone()
        if not profile:
            # Nếu không có default, lấy profile đầu tiên
            cur = conn.execute("SELECT * FROM health_profiles WHERE user_id=? ORDER BY created_at LIMIT 1", (user_id,))
            profile = cur.fetchone()
        return profile


def update_health_profile(profile_id: int, user_id: int, **updates) -> bool:
    """Cập nhật hồ sơ sức khỏe"""
    with get_conn() as conn:
        profile = conn.execute("SELECT * FROM health_profiles WHERE id=? AND user_id=?", (profile_id, user_id)).fetchone()
        if not profile:
            return False
        
        # Nếu set làm default, unset các profiles khác
        if updates.get('is_default'):
            conn.execute("UPDATE health_profiles SET is_default = 0 WHERE user_id = ? AND id != ?", (user_id, profile_id))
        
        # Build update query
        set_clauses = []
        values = []
        for key, value in updates.items():
            if key == 'conditions_json' and value is not None:
                value = json.dumps(value, ensure_ascii=False)
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        if set_clauses:
            set_clauses.append("updated_at = ?")
            values.extend([_now(), profile_id, user_id])
            query = f"UPDATE health_profiles SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?"
            conn.execute(query, values)
        
        return True


def delete_health_profile(profile_id: int, user_id: int) -> bool:
    """Xóa hồ sơ sức khỏe (cascade sẽ xóa documents và chats)"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM health_profiles WHERE id=? AND user_id=?", (profile_id, user_id))
        return cur.rowcount > 0


# ====== DOCUMENTS MANAGEMENT ======
def add_document(health_profile_id: int, filename: str, original_content: str, 
                ai_summary: str, file_type: str = 'pdf', file_size: int = 0) -> int:
    """Thêm tài liệu y tế"""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO documents(health_profile_id, filename, original_content, ai_summary, 
               file_type, file_size, uploaded_at) VALUES (?,?,?,?,?,?,?)""",
            (health_profile_id, filename, original_content, ai_summary, file_type, file_size, _now()),
        )
        return int(cur.lastrowid)


def list_documents(health_profile_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Lấy danh sách tài liệu theo profile"""
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, filename, ai_summary, file_type, file_size, uploaded_at 
               FROM documents WHERE health_profile_id=? ORDER BY uploaded_at DESC LIMIT ?""",
            (health_profile_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def get_document(doc_id: int, health_profile_id: int) -> Optional[sqlite3.Row]:
    """Lấy chi tiết tài liệu (với ownership check)"""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM documents WHERE id=? AND health_profile_id=?", (doc_id, health_profile_id))
        return cur.fetchone()


# ====== CHAT MANAGEMENT ======
def create_chat_session(health_profile_id: int, session_name: Optional[str] = None) -> int:
    """Tạo phiên chat mới"""
    if not session_name:
        session_name = f"Chat {_now()[:10]}"
    
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chat_sessions(health_profile_id, session_name, started_at, last_message_at) VALUES (?,?,?,?)",
            (health_profile_id, session_name, _now(), _now()),
        )
        return int(cur.lastrowid)


def list_chat_sessions(health_profile_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Lấy danh sách phiên chat"""
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, session_name, started_at, last_message_at,
               (SELECT COUNT(*) FROM chat_messages WHERE session_id = chat_sessions.id) as message_count
               FROM chat_sessions WHERE health_profile_id=? ORDER BY last_message_at DESC LIMIT ?""",
            (health_profile_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def add_chat_message(session_id: int, role: str, content: str, 
                    message_type: str = 'text', metadata: Optional[Dict] = None) -> int:
    """Thêm tin nhắn vào session"""
    with get_conn() as conn:
        # Thêm message
        cur = conn.execute(
            """INSERT INTO chat_messages(session_id, role, content, message_type, metadata_json, created_at) 
               VALUES (?,?,?,?,?,?)""",
            (session_id, role, content, message_type, json.dumps(metadata or {}), _now()),
        )
        
        # Cập nhật last_message_at của session
        conn.execute("UPDATE chat_sessions SET last_message_at = ? WHERE id = ?", (_now(), session_id))
        
        return int(cur.lastrowid)


def list_chat_messages(session_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Lấy tin nhắn trong session"""
    with get_conn() as conn:
        cur = conn.execute(
            """SELECT id, role, content, message_type, metadata_json, created_at 
               FROM chat_messages WHERE session_id=? ORDER BY id DESC LIMIT ?""",
            (session_id, limit),
        )
        messages = []
        for r in cur.fetchall():
            msg = dict(r)
            try:
                msg['metadata'] = json.loads(r['metadata_json']) if r['metadata_json'] else {}
            except:
                msg['metadata'] = {}
            del msg['metadata_json']
            messages.append(msg)
        return list(reversed(messages))  # Oldest first


def search_food_by_name(name: str) -> List[Dict[str, Any]]:
    like = f"%{name.strip()}%"
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT id, name, category, subcategory, nutrients_json, contraindications_json,
                   benefits_json, recommended_portions_json, preparation_notes
            FROM foods
            WHERE name LIKE ? OR category LIKE ?
            ORDER BY name LIMIT 10
            """,
            (like, like),
        )
        rows = cur.fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            item: Dict[str, Any] = {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "subcategory": r["subcategory"],
                "preparation_notes": r["preparation_notes"],
            }
            for field in [
                ("nutrients_json", "nutrients", {}),
                ("contraindications_json", "contraindications", []),
                ("benefits_json", "benefits", []),
                ("recommended_portions_json", "recommended_portions", {}),
            ]:
                src, dst, default = field
                try:
                    item[dst] = json.loads(r[src]) if r[src] else default
                except Exception:
                    item[dst] = default
            results.append(item)
        return results


def list_foods(query: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        if query:
            like = f"%{query.strip()}%"
            cur = conn.execute(
                """
                SELECT id, name, category, subcategory, nutrients_json, contraindications_json,
                       benefits_json, recommended_portions_json, preparation_notes
                FROM foods
                WHERE name LIKE ? OR category LIKE ? OR subcategory LIKE ?
                ORDER BY name LIMIT ? OFFSET ?
                """,
                (like, like, like, limit, offset),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, name, category, subcategory, nutrients_json, contraindications_json,
                       benefits_json, recommended_portions_json, preparation_notes
                FROM foods
                ORDER BY name LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        rows = cur.fetchall()
        items: List[Dict[str, Any]] = []
        for r in rows:
            item: Dict[str, Any] = {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"],
                "subcategory": r["subcategory"],
                "preparation_notes": r["preparation_notes"],
            }
            for field in [
                ("nutrients_json", "nutrients", {}),
                ("contraindications_json", "contraindications", []),
                ("benefits_json", "benefits", []),
                ("recommended_portions_json", "recommended_portions", {}),
            ]:
                src, dst, default = field
                try:
                    item[dst] = json.loads(r[src]) if r[src] else default
                except Exception:
                    item[dst] = default
            items.append(item)
        return items


# ====== FOODS MANAGEMENT (Enhanced) ======
def create_food(item: Dict[str, Any], created_by: Optional[int] = None) -> int:
    """Tạo thực phẩm mới"""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO foods(name, category, subcategory, nutrients_json, contraindications_json, 
               benefits_json, recommended_portions_json, preparation_notes, source_reliability, 
               created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item.get("name"),
                item.get("category"),
                item.get("subcategory"),
                json.dumps(item.get("nutrients") or {}, ensure_ascii=False),
                json.dumps(item.get("contraindications") or [], ensure_ascii=False),
                json.dumps(item.get("benefits") or [], ensure_ascii=False),
                json.dumps(item.get("recommended_portions") or {}, ensure_ascii=False),
                item.get("preparation_notes"),
                item.get("source_reliability", "verified"),
                created_by,
                _now(),
                _now(),
            ),
        )
        return int(cur.lastrowid)


def update_food(food_id: int, item: Dict[str, Any]) -> bool:
    """Cập nhật thực phẩm"""
    with get_conn() as conn:
        current = conn.execute("SELECT * FROM foods WHERE id=?", (food_id,)).fetchone()
        if not current:
            return False
        
        # Update fields
        updates = {}
        if "name" in item: updates["name"] = item["name"]
        if "category" in item: updates["category"] = item["category"]
        if "subcategory" in item: updates["subcategory"] = item["subcategory"]
        if "nutrients" in item: updates["nutrients_json"] = json.dumps(item["nutrients"], ensure_ascii=False)
        if "contraindications" in item: updates["contraindications_json"] = json.dumps(item["contraindications"], ensure_ascii=False)
        if "benefits" in item: updates["benefits_json"] = json.dumps(item["benefits"], ensure_ascii=False)
        if "recommended_portions" in item: updates["recommended_portions_json"] = json.dumps(item["recommended_portions"], ensure_ascii=False)
        if "preparation_notes" in item: updates["preparation_notes"] = item["preparation_notes"]
        
        if updates:
            updates["updated_at"] = _now()
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [food_id]
            conn.execute(f"UPDATE foods SET {set_clause} WHERE id = ?", values)
        
        return True


def delete_food(food_id: int) -> bool:
    """Xóa thực phẩm"""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM foods WHERE id=?", (food_id,))
        return cur.rowcount > 0


def get_food_by_id(food_id: int) -> Optional[Dict[str, Any]]:
    """Lấy thông tin thực phẩm theo ID"""
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM foods WHERE id=?", (food_id,))
        row = cur.fetchone()
        if not row:
            return None
        
        food = dict(row)
        # Parse JSON fields
        for field in ['nutrients_json', 'contraindications_json', 'benefits_json', 'recommended_portions_json']:
            try:
                key = field.replace('_json', '')
                food[key] = json.loads(row[field]) if row[field] else ({} if 'nutrients' in field or 'portions' in field else [])
            except:
                food[key] = {} if 'nutrients' in field or 'portions' in field else []
            del food[field]
        
        return food


# ====== STATISTICS ======
def get_stats() -> Dict[str, int]:
    """Lấy thống kê hệ thống"""
    with get_conn() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_active = 1").fetchone()["c"]
        profiles = conn.execute("SELECT COUNT(*) AS c FROM health_profiles").fetchone()["c"]
        docs = conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]
        foods = conn.execute("SELECT COUNT(*) AS c FROM foods").fetchone()["c"]
        sessions = conn.execute("SELECT COUNT(*) AS c FROM chat_sessions").fetchone()["c"]
        messages = conn.execute("SELECT COUNT(*) AS c FROM chat_messages").fetchone()["c"]
        
        return {
            "users": users,
            "health_profiles": profiles,
            "documents": docs,
            "foods": foods,
            "chat_sessions": sessions,
            "chat_messages": messages
        }


def get_user_stats(user_id: int) -> Dict[str, int]:
    """Lấy thống kê của 1 user"""
    with get_conn() as conn:
        profiles = conn.execute("SELECT COUNT(*) AS c FROM health_profiles WHERE user_id = ?", (user_id,)).fetchone()["c"]
        docs = conn.execute(
            "SELECT COUNT(*) AS c FROM documents d JOIN health_profiles hp ON d.health_profile_id = hp.id WHERE hp.user_id = ?", 
            (user_id,)
        ).fetchone()["c"]
        sessions = conn.execute(
            "SELECT COUNT(*) AS c FROM chat_sessions cs JOIN health_profiles hp ON cs.health_profile_id = hp.id WHERE hp.user_id = ?", 
            (user_id,)
        ).fetchone()["c"]
        
        return {"profiles": profiles, "documents": docs, "chat_sessions": sessions}


# ====== HEALTH PLANNING FUNCTIONS ======

def create_health_plan(
    health_profile_id: int,
    title: str,
    goal_type: str,
    target_value: float,
    target_unit: str,
    duration_days: int,
    start_date: str,
    available_activities: List[str] = None,
    dietary_restrictions: List[str] = None,
    ai_analysis: Dict[str, Any] = None
) -> int:
    """Tạo kế hoạch sức khỏe mới"""
    from datetime import datetime, timedelta
    
    start_dt = datetime.fromisoformat(start_date)
    end_dt = start_dt + timedelta(days=duration_days)
    
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO health_plans (
                health_profile_id, title, goal_type, target_value, target_unit,
                duration_days, start_date, end_date, current_progress, status,
                available_activities_json, dietary_restrictions_json, ai_analysis_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                health_profile_id, title, goal_type, target_value, target_unit,
                duration_days, start_date, end_dt.isoformat(), 0.0, "active",
                json.dumps(available_activities or [], ensure_ascii=False),
                json.dumps(dietary_restrictions or [], ensure_ascii=False),
                json.dumps(ai_analysis or {}, ensure_ascii=False),
                _now(), _now()
            )
        )
        return cur.lastrowid

def get_health_plans(health_profile_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy danh sách kế hoạch sức khỏe"""
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM health_plans WHERE health_profile_id = ? AND status = ? ORDER BY created_at DESC",
                (health_profile_id, status)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM health_plans WHERE health_profile_id = ? ORDER BY created_at DESC",
                (health_profile_id,)
            ).fetchall()
        
        plans = []
        for row in rows:
            plan = dict(row)
            # Parse JSON fields
            for field in ['available_activities_json', 'dietary_restrictions_json', 'ai_analysis_json']:
                try:
                    plan[field.replace('_json', '')] = json.loads(plan[field]) if plan[field] else []
                except Exception:
                    plan[field.replace('_json', '')] = []
            plans.append(plan)
        return plans

def get_health_plan(plan_id: int, health_profile_id: int) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết kế hoạch sức khỏe"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM health_plans WHERE id = ? AND health_profile_id = ?",
            (plan_id, health_profile_id)
        ).fetchone()
        
        if not row:
            return None
            
        plan = dict(row)
        # Parse JSON fields
        for field in ['available_activities_json', 'dietary_restrictions_json', 'ai_analysis_json']:
            try:
                plan[field.replace('_json', '')] = json.loads(plan[field]) if plan[field] else []
            except Exception:
                plan[field.replace('_json', '')] = []
        return plan

def update_health_plan(plan_id: int, health_profile_id: int, **updates) -> bool:
    """Cập nhật kế hoạch sức khỏe"""
    if not updates:
        return True
        
    # Build dynamic UPDATE query
    set_clauses = []
    values = []
    
    for key, value in updates.items():
        if key in ['title', 'status', 'current_progress', 'target_value']:
            set_clauses.append(f"{key} = ?")
            values.append(value)
    
    if not set_clauses:
        return True
        
    set_clauses.append("updated_at = ?")
    values.append(_now())
    values.extend([plan_id, health_profile_id])
    
    with get_conn() as conn:
        conn.execute(
            f"UPDATE health_plans SET {', '.join(set_clauses)} WHERE id = ? AND health_profile_id = ?",
            values
        )
        return conn.total_changes > 0

def delete_health_plan(plan_id: int, health_profile_id: int) -> bool:
    """Xóa kế hoạch sức khỏe"""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM health_plans WHERE id = ? AND health_profile_id = ?",
            (plan_id, health_profile_id)
        )
        return conn.total_changes > 0

# ====== ACTIVITY PLANNING ======

def add_plan_activity(
    health_plan_id: int,
    date: str,
    activity_type: str,
    activity_name: str,
    duration_minutes: int,
    intensity: str,
    calories_target: Optional[float] = None,
    instructions: Optional[str] = None
) -> int:
    """Thêm hoạt động vào kế hoạch"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO health_plan_activities (
                health_plan_id, date, activity_type, activity_name,
                duration_minutes, intensity, calories_target, instructions, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                health_plan_id, date, activity_type, activity_name,
                duration_minutes, intensity, calories_target, instructions, _now()
            )
        )
        return cur.lastrowid

def get_plan_activities(health_plan_id: int, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy hoạt động trong kế hoạch"""
    with get_conn() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM health_plan_activities WHERE health_plan_id = ? AND date = ? ORDER BY created_at",
                (health_plan_id, date)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM health_plan_activities WHERE health_plan_id = ? ORDER BY date, created_at",
                (health_plan_id,)
            ).fetchall()
        return [dict(row) for row in rows]

def complete_plan_activity(activity_id: int, actual_duration: int, actual_intensity: str, notes: Optional[str] = None) -> bool:
    """Hoàn thành hoạt động trong kế hoạch"""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE health_plan_activities 
            SET is_completed = 1, completed_at = ?, actual_duration_minutes = ?, actual_intensity = ?, notes = ?
            WHERE id = ?
            """,
            (_now(), actual_duration, actual_intensity, notes, activity_id)
        )
        return conn.total_changes > 0

def update_plan_activity(
    activity_id: int,
    activity_type: Optional[str] = None,
    activity_name: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    intensity: Optional[str] = None,
    calories_target: Optional[float] = None,
    instructions: Optional[str] = None
) -> bool:
    """Cập nhật thuộc tính hoạt động trong kế hoạch"""
    fields = []
    values = []
    if activity_type is not None:
        fields.append("activity_type = ?"); values.append(activity_type)
    if activity_name is not None:
        fields.append("activity_name = ?"); values.append(activity_name)
    if duration_minutes is not None:
        fields.append("duration_minutes = ?"); values.append(duration_minutes)
    if intensity is not None:
        fields.append("intensity = ?"); values.append(intensity)
    if calories_target is not None:
        fields.append("calories_target = ?"); values.append(calories_target)
    if instructions is not None:
        fields.append("instructions = ?"); values.append(instructions)
    if not fields:
        return False
    with get_conn() as conn:
        sql = f"UPDATE health_plan_activities SET {', '.join(fields)} WHERE id = ?"
        conn.execute(sql, (*values, activity_id))
        return conn.total_changes > 0

# ====== MEAL PLANNING ======

def add_plan_meal(
    health_plan_id: int,
    date: str,
    meal_type: str,
    food_items: List[Dict[str, Any]],
    total_calories: Optional[float] = None,
    macros: Optional[Dict[str, float]] = None,
    preparation_notes: Optional[str] = None
) -> int:
    """Thêm bữa ăn vào kế hoạch"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO health_plan_meals (
                health_plan_id, date, meal_type, food_items_json,
                total_calories, macros_json, preparation_notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                health_plan_id, date, meal_type, json.dumps(food_items, ensure_ascii=False),
                total_calories, json.dumps(macros or {}, ensure_ascii=False), preparation_notes, _now()
            )
        )
        return cur.lastrowid

def get_plan_meals(health_plan_id: int, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy bữa ăn trong kế hoạch"""
    with get_conn() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM health_plan_meals WHERE health_plan_id = ? AND date = ? ORDER BY meal_type",
                (health_plan_id, date)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM health_plan_meals WHERE health_plan_id = ? ORDER BY date, meal_type",
                (health_plan_id,)
            ).fetchall()
        
        meals = []
        for row in rows:
            meal = dict(row)
            # Parse JSON fields
            try:
                meal['food_items'] = json.loads(meal['food_items_json']) if meal['food_items_json'] else []
            except Exception:
                meal['food_items'] = []
            try:
                meal['macros'] = json.loads(meal['macros_json']) if meal['macros_json'] else {}
            except Exception:
                meal['macros'] = {}
            meals.append(meal)
        return meals

def complete_plan_meal(meal_id: int, actual_foods: List[Dict[str, Any]], deviation_notes: Optional[str] = None) -> bool:
    """Hoàn thành bữa ăn trong kế hoạch"""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE health_plan_meals 
            SET is_completed = 1, completed_at = ?, actual_foods_json = ?, deviation_notes = ?
            WHERE id = ?
            """,
            (_now(), json.dumps(actual_foods, ensure_ascii=False), deviation_notes, meal_id)
        )
        return conn.total_changes > 0

# ====== ACTIVITY & MEAL LOGGING ======

def log_activity(
    health_profile_id: int,
    date: str,
    activity_type: str,
    activity_name: str,
    duration_minutes: int,
    intensity: str,
    calories_burned: Optional[float] = None,
    notes: Optional[str] = None,
    source: str = "manual",
    activity_plan_id: Optional[int] = None
) -> int:
    """Ghi nhận hoạt động đã thực hiện"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO activity_logs (
                health_profile_id, activity_plan_id, date, activity_type, activity_name,
                duration_minutes, intensity, calories_burned, notes, source, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                health_profile_id, activity_plan_id, date, activity_type, activity_name,
                duration_minutes, intensity, calories_burned, notes, source, _now()
            )
        )
        return cur.lastrowid

def log_meal(
    health_profile_id: int,
    date: str,
    meal_type: str,
    food_items: List[Dict[str, Any]],
    total_calories: Optional[float] = None,
    notes: Optional[str] = None,
    source: str = "manual",
    meal_plan_id: Optional[int] = None
) -> int:
    """Ghi nhận bữa ăn đã thực hiện"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO meal_logs (
                health_profile_id, meal_plan_id, date, meal_type,
                food_items_json, total_calories, notes, source, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                health_profile_id, meal_plan_id, date, meal_type,
                json.dumps(food_items, ensure_ascii=False), total_calories, notes, source, _now()
            )
        )
        return cur.lastrowid

def get_activity_logs(health_profile_id: int, date: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Lấy lịch sử hoạt động"""
    with get_conn() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM activity_logs WHERE health_profile_id = ? AND date = ? ORDER BY logged_at DESC LIMIT ?",
                (health_profile_id, date, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM activity_logs WHERE health_profile_id = ? ORDER BY date DESC, logged_at DESC LIMIT ?",
                (health_profile_id, limit)
            ).fetchall()
        return [dict(row) for row in rows]

def get_meal_logs(health_profile_id: int, date: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Lấy lịch sử bữa ăn"""
    with get_conn() as conn:
        if date:
            rows = conn.execute(
                "SELECT * FROM meal_logs WHERE health_profile_id = ? AND date = ? ORDER BY logged_at DESC LIMIT ?",
                (health_profile_id, date, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM meal_logs WHERE health_profile_id = ? ORDER BY date DESC, logged_at DESC LIMIT ?",
                (health_profile_id, limit)
            ).fetchall()
        
        meals = []
        for row in rows:
            meal = dict(row)
            try:
                meal['food_items'] = json.loads(meal['food_items_json']) if meal['food_items_json'] else []
            except Exception:
                meal['food_items'] = []
            meals.append(meal)
        return meals

def get_daily_plan_summary(health_plan_id: int, date: str) -> Dict[str, Any]:
    """Lấy tóm tắt kế hoạch hàng ngày"""
    activities = get_plan_activities(health_plan_id, date)
    meals = get_plan_meals(health_plan_id, date)
    
    total_calories_target = sum(meal.get('total_calories', 0) for meal in meals)
    
    # Calculate completion rate
    total_tasks = len(activities) + len(meals)
    completed_tasks = sum(1 for a in activities if a.get('is_completed')) + sum(1 for m in meals if m.get('is_completed'))
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        "date": date,
        "activities": activities,
        "meals": meals,
        "total_calories_target": total_calories_target,
        "completion_rate": completion_rate
    }

