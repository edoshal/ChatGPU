"""
Service to build and run a LangChain agent for the chatbot.
"""
import os
import json
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from . import db

def create_chatbot_agent(user_id: int, profile_id: int, session_data: Dict[str, Any]) -> AgentExecutor:
    """Tạo một AgentExecutor để xử lý logic chatbot."""

    # === Định nghĩa Tools bên trong hàm để sử dụng closure ===
    @tool
    def search_food_database(food_name: str) -> Dict[str, Any]:
        """Tra cứu thông tin chi tiết về một loại thực phẩm cụ thể trong cơ sở dữ liệu. Chỉ sử dụng khi bạn không chắc chắn về một loại thực phẩm đặc thù hoặc địa phương."""
        foods = db.search_food_by_name(food_name)
        if foods:
            food = foods[0]
            return {
                "name": food.get("name", ""), "category": food.get("category", ""),
                "nutrients": food.get("nutrients", {}), "contraindications": food.get("contraindications", []),
                "recommended_portions": food.get("recommended_portions", {}), "preparation_notes": food.get("preparation_notes", ""),
            }
        return {"error": f"Không tìm thấy thông tin về '{food_name}' trong cơ sở dữ liệu."}

    @tool
    def update_health_status(new_conditions: List[str] = [], condition_text_update: str = "", weight_delta_kg: Optional[float] = None, new_weight_kg: Optional[float] = None, new_height_cm: Optional[float] = None, age: Optional[int] = None, gender: Optional[str] = None) -> Dict[str, Any]:
        """Cập nhật hồ sơ sức khỏe khi người dùng chia sẻ thông tin về tuổi, cân nặng, chiều cao, tình trạng bệnh lý. Luôn gọi tool này khi có thông tin mới."""
        current_conditions = session_data.get("conditions_json", "{}")
        if isinstance(current_conditions, str):
            try:
                conditions_data = json.loads(current_conditions)
                if not isinstance(conditions_data, dict): conditions_data = {"conditions_list": []}
            except Exception:
                conditions_data = {"conditions_list": []}
        else:
            conditions_data = current_conditions or {"conditions_list": []}

        if not isinstance(conditions_data, dict): conditions_data = {"conditions_list": []}

        existing_conditions = conditions_data.get("conditions_list", [])
        for condition in new_conditions:
            if condition and condition not in existing_conditions: existing_conditions.append(condition)
        conditions_data["conditions_list"] = existing_conditions

        update_data: Dict[str, Any] = {"conditions_json": json.dumps(conditions_data, ensure_ascii=False)}

        if condition_text_update:
            current_text = session_data.get("conditions_text", "")
            update_data["conditions_text"] = (f"{current_text}\n{condition_text_update}" if current_text else condition_text_update)

        if age is not None: update_data["age"] = age
        if gender:
            gender_mapping = {"Nam": "male", "Nữ": "female", "Khác": "other", "male": "male", "female": "female", "other": "other"}
            if mapped_gender := gender_mapping.get(gender): update_data["gender"] = mapped_gender
        if new_height_cm is not None: update_data["height"] = new_height_cm

        current_weight = session_data.get("weight")
        if new_weight_kg is not None:
            update_data["weight"] = new_weight_kg
        elif weight_delta_kg is not None and current_weight is not None:
            try: update_data["weight"] = float(current_weight) + float(weight_delta_kg)
            except Exception: pass

        db.update_health_profile(profile_id, user_id, **update_data)
        return {"success": True, "message": "Đã cập nhật tình trạng sức khỏe thành công.", "updated_fields": list(update_data.keys())}

    tools = [search_food_database, update_health_status]

    # Khởi tạo LLM
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        temperature=0.2,
        streaming=False
    )

    # Tạo system prompt
    profile_context = f"""THÔNG TIN NGƯỜI DÙNG:
- Hồ sơ: {session_data.get('profile_name', 'Không rõ')}
- Tuổi: {session_data.get('age', 'chưa có')}
- Giới tính: {session_data.get('gender', 'chưa có')}
- Cân nặng hiện tại: {session_data.get('weight', 'chưa có')} kg
- Chiều cao: {session_data.get('height', 'chưa có')} cm
- Tình trạng sức khỏe: {session_data.get('conditions_text', 'Chưa có thông tin')}
"""

    system_prompt_template = f"""Bạn là chuyên gia tư vấn sức khỏe và dinh dưỡng. Nhiệm vụ của bạn:

1. TƯ VẤN THỰC PHẨM:
   - Sử dụng kiến thức chuyên môn của bạn để tư vấn về thực phẩm
   - Đưa ra lời khuyên dựa trên tình trạng sức khỏe cụ thể của người dùng
   - Chỉ sử dụng function search_food_database khi gặp thực phẩm đặc thù/địa phương mà bạn không chắc chắn

2. CẬP NHẬT THÔNG TIN SỨC KHỎE:
   - QUAN TRỌNG: Khi người dùng chia sẻ bất kỳ thông tin cá nhân nào về sức khỏe, hãy LUÔN gọi function update_health_status

3. NGUYÊN TẮC TƯ VẤN:
   - Ưu tiên an toàn sức khỏe
   - Đưa ra lời khuyên cụ thể, thực tế
   - Khuyến nghị tham khảo bác sĩ khi cần thiết

{profile_context}

Hãy trả lời một cách chuyên nghiệp, thân thiện và dựa trên bằng chứng khoa học."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    return agent_executor

