import csv
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "chatgpu.db"))
SCHEMA_VERSION = 2


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
        
        # Indexes for performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_health_profiles_user ON health_profiles(user_id);")
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


