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

    @tool
    def log_daily_activity(activity_name: str, duration_minutes: int, intensity: str = "medium", notes: str = "") -> Dict[str, Any]:
        """Ghi nhận hoạt động thể thao đã thực hiện hôm nay. Sử dụng khi người dùng báo cáo đã tập luyện, chơi thể thao."""
        from datetime import date
        import re
        
        # Validate intensity
        valid_intensities = ["low", "medium", "high"]
        if intensity.lower() not in valid_intensities:
            intensity = "medium"
        
        # Estimate activity type based on name
        activity_type = "general"
        activity_lower = activity_name.lower()
        if any(word in activity_lower for word in ["bơi", "swim"]):
            activity_type = "swimming"
        elif any(word in activity_lower for word in ["chạy", "run", "jog"]):
            activity_type = "running"
        elif any(word in activity_lower for word in ["đá bóng", "football", "soccer"]):
            activity_type = "football"
        elif any(word in activity_lower for word in ["cầu lông", "badminton"]):
            activity_type = "badminton"
        elif any(word in activity_lower for word in ["gym", "tập gym", "tạ"]):
            activity_type = "gym"
        elif any(word in activity_lower for word in ["đi bộ", "walk"]):
            activity_type = "walking"
        elif any(word in activity_lower for word in ["yoga"]):
            activity_type = "yoga"
        
        # Estimate calories (rough calculation)
        calories_map = {
            "swimming": 8, "running": 10, "football": 7, "badminton": 6,
            "gym": 6, "walking": 4, "yoga": 3, "general": 5
        }
        intensity_multiplier = {"low": 0.7, "medium": 1.0, "high": 1.3}
        
        calories_burned = duration_minutes * calories_map.get(activity_type, 5) * intensity_multiplier.get(intensity, 1.0)
        
        try:
            log_id = db.log_activity(
                health_profile_id=profile_id,
                date=date.today().isoformat(),
                activity_type=activity_type,
                activity_name=activity_name,
                duration_minutes=duration_minutes,
                intensity=intensity.lower(),
                calories_burned=calories_burned,
                notes=notes,
                source="chat"
            )
            return {
                "success": True,
                "message": f"Đã ghi nhận hoạt động '{activity_name}' ({duration_minutes} phút, {intensity})",
                "log_id": log_id,
                "estimated_calories": round(calories_burned, 1)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @tool
    def log_daily_meal(meal_type: str, food_description: str, estimated_calories: int = None, notes: str = "") -> Dict[str, Any]:
        """Ghi nhận bữa ăn đã thực hiện. Sử dụng khi người dùng báo cáo đã ăn gì."""
        from datetime import date
        
        # Validate meal type
        valid_meals = ["breakfast", "lunch", "dinner", "snack"]
        meal_lower = meal_type.lower()
        if "sáng" in meal_lower or "breakfast" in meal_lower:
            meal_type = "breakfast"
        elif "trưa" in meal_lower or "lunch" in meal_lower:
            meal_type = "lunch"
        elif "tối" in meal_lower or "dinner" in meal_lower:
            meal_type = "dinner"
        elif "snack" in meal_lower or "ăn vặt" in meal_lower:
            meal_type = "snack"
        else:
            meal_type = "snack"  # default
        
        # Parse food items from description
        food_items = [{
            "name": food_description,
            "amount": "1 phần",
            "calories": estimated_calories or 300,  # default estimate
            "source": "user_report"
        }]
        
        try:
            log_id = db.log_meal(
                health_profile_id=profile_id,
                date=date.today().isoformat(),
                meal_type=meal_type,
                food_items=food_items,
                total_calories=estimated_calories,
                notes=notes,
                source="chat"
            )
            return {
                "success": True,
                "message": f"Đã ghi nhận bữa {meal_type}: {food_description}",
                "log_id": log_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @tool
    def get_active_health_plans() -> Dict[str, Any]:
        """Lấy kế hoạch sức khỏe đang hoạt động của người dùng."""
        try:
            plans = db.get_health_plans(profile_id, status="active")
            if not plans:
                return {"message": "Hiện tại chưa có kế hoạch sức khỏe nào đang hoạt động."}
            
            active_plan = plans[0]  # Get the most recent active plan
            return {
                "plan_id": active_plan["id"],
                "title": active_plan["title"],
                "goal_type": active_plan["goal_type"],
                "target_value": active_plan["target_value"],
                "target_unit": active_plan["target_unit"],
                "current_progress": active_plan["current_progress"],
                "start_date": active_plan["start_date"],
                "end_date": active_plan["end_date"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @tool
    def get_today_plan_summary() -> Dict[str, Any]:
        """Lấy tóm tắt kế hoạch hôm nay (hoạt động và bữa ăn)."""
        from datetime import date
        
        try:
            # Get active plan
            plans = db.get_health_plans(profile_id, status="active")
            if not plans:
                return {"message": "Chưa có kế hoạch sức khỏe đang hoạt động."}
            
            plan_id = plans[0]["id"]
            today = date.today().isoformat()
            
            summary = db.get_daily_plan_summary(plan_id, today)
            
            return {
                "date": today,
                "total_activities": len(summary["activities"]),
                "completed_activities": len([a for a in summary["activities"] if a.get("is_completed")]),
                "total_meals": len(summary["meals"]),
                "completed_meals": len([m for m in summary["meals"] if m.get("is_completed")]),
                "completion_rate": summary["completion_rate"],
                "target_calories": summary["total_calories_target"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @tool
    def complete_planned_activity(activity_description: str, actual_duration: int = None, notes: str = "") -> Dict[str, Any]:
        """Đánh dấu hoàn thành hoạt động trong kế hoạch hôm nay. Sử dụng khi người dùng báo cáo đã thực hiện hoạt động theo kế hoạch."""
        from datetime import date
        
        try:
            # Get active plan
            plans = db.get_health_plans(profile_id, status="active")
            if not plans:
                return {"message": "Chưa có kế hoạch sức khỏe đang hoạt động."}
            
            plan_id = plans[0]["id"]
            today = date.today().isoformat()
            
            # Get today's activities
            activities = db.get_plan_activities(plan_id, today)
            
            # Find matching activity
            for activity in activities:
                if not activity.get("is_completed") and activity_description.lower() in activity["activity_name"].lower():
                    success = db.complete_plan_activity(
                        activity["id"],
                        actual_duration or activity["duration_minutes"],
                        activity["intensity"],
                        notes
                    )
                    if success:
                        return {
                            "success": True,
                            "message": f"Đã hoàn thành hoạt động: {activity['activity_name']}",
                            "activity_id": activity["id"]
                        }
            
            return {"message": f"Không tìm thấy hoạt động '{activity_description}' trong kế hoạch hôm nay."}
            
        except Exception as e:
            return {"error": str(e)}

    tools = [search_food_database, update_health_status, log_daily_activity, log_daily_meal, get_active_health_plans, get_today_plan_summary, complete_planned_activity]

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

TÍNH NĂNG THEO DÕI KẾ HOẠCH SỨC KHỊE:
- Khi người dùng báo cáo hoạt động: Sử dụng log_daily_activity
- Khi người dùng báo cáo bữa ăn: Sử dụng log_daily_meal  
- Khi hỏi về kế hoạch: Sử dụng get_active_health_plans và get_today_plan_summary
- Khi hoàn thành hoạt động theo kế hoạch: Sử dụng complete_planned_activity

LUÔN phân tích sự khác biệt giữa kế hoạch và thực tế, đưa ra gợi ý điều chỉnh.

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

