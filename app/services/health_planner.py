"""
Health Planning AI Service
Tạo kế hoạch sức khỏe tự động dựa trên profile người dùng và mục tiêu
"""
import json
import os
import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from . import db

# Setup logger
logger = logging.getLogger(__name__)


class HealthPlannerService:
    """Service để tạo và quản lý kế hoạch sức khỏe bằng AI"""
    
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
            temperature=0.3,
            streaming=False
        )
    
    def create_health_plan(
        self,
        health_profile_id: int,
        title: str,
        goal_type: str,
        target_value: float,
        target_unit: str,
        duration_days: int,
        start_date: date,
        available_activities: List[str],
        dietary_restrictions: List[str] = None,
        profile_data: Dict[str, Any] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Tạo kế hoạch sức khỏe chi tiết với AI
        
        Returns:
            Tuple[plan_id, ai_analysis] - ID kế hoạch và phân tích AI
        """
        
        # Lấy thông tin profile nếu chưa có
        if not profile_data:
            with db.get_conn() as conn:
                profile_data = conn.execute(
                    "SELECT * FROM health_profiles WHERE id = ?", (health_profile_id,)
                ).fetchone()
                if profile_data:
                    profile_data = dict(profile_data)
        
        # Tạo AI analysis
        ai_analysis = self._analyze_health_plan(
            profile_data, goal_type, target_value, target_unit, 
            duration_days, available_activities, dietary_restrictions
        )
        
        # Tạo plan trong database
        try:
            logger.info(f"Creating health plan for profile {health_profile_id}")
            plan_id = db.create_health_plan(
                health_profile_id=health_profile_id,
                title=title,
                goal_type=goal_type,
                target_value=target_value,
                target_unit=target_unit,
                duration_days=duration_days,
                start_date=start_date.isoformat(),
                available_activities=available_activities,
                dietary_restrictions=dietary_restrictions or [],
                ai_analysis=ai_analysis
            )
            logger.info(f"Created health plan with ID: {plan_id}")
        except Exception as e:
            logger.error(f"Error creating health plan in database: {str(e)}")
            raise
        
        # Tạo lịch trình chi tiết
        try:
            logger.info(f"Generating detailed schedule for plan {plan_id}")
            self._generate_detailed_schedule(plan_id, start_date, duration_days, ai_analysis)
            logger.info(f"Successfully generated schedule for plan {plan_id}")
        except Exception as e:
            logger.error(f"Error generating detailed schedule: {str(e)}")
            # Xóa plan nếu tạo lịch trình thất bại
            try:
                db.delete_health_plan(plan_id, health_profile_id)
                logger.info(f"Deleted plan {plan_id} due to schedule generation failure")
            except:
                pass
            raise
        
        return plan_id, ai_analysis
    
    def _analyze_health_plan(
        self,
        profile_data: Dict[str, Any],
        goal_type: str,
        target_value: float,
        target_unit: str,
        duration_days: int,
        available_activities: List[str],
        dietary_restrictions: List[str] = None
    ) -> Dict[str, Any]:
        """Phân tích và đưa ra khuyến nghị bằng AI"""
        
        prompt_template = ChatPromptTemplate.from_template("""
Bạn là chuyên gia dinh dưỡng và thể thao. Phân tích thông tin sau và tạo kế hoạch sức khỏe chi tiết:

THÔNG TIN NGƯỜI DÙNG:
- Tuổi: {age}
- Giới tính: {gender}
- Cân nặng hiện tại: {weight} kg
- Chiều cao: {height} cm
- Tình trạng sức khỏe: {conditions}

MỤC TIÊU:
- Loại: {goal_type}
- Giá trị: {target_value} {target_unit}
- Thời gian: {duration_days} ngày

ĐIỀU KIỆN:
- Hoạt động có thể thực hiện: {activities}
- Hạn chế ăn uống: {restrictions}

QUAN TRỌNG: Bạn PHẢI sử dụng các hoạt động được liệt kê ở trên trong exercise_recommendations. 
Không được tạo ra hoạt động mới không có trong danh sách. 
Nếu có nhiều hoạt động, hãy phân bố chúng đều trong tuần.

Hãy phân tích và trả về JSON với các trường:
{{
  "feasibility_score": (số từ 1-10, 10 là khả thi nhất),
  "weekly_targets": [
    {{
      "week": 1,
      "target_progress": (% hoàn thành mục tiêu),
      "focus": "Mô tả trọng tâm tuần này"
    }}
  ],
  "exercise_recommendations": [
    {{
      "activity": "tên hoạt động (PHẢI là một trong các hoạt động được liệt kê ở trên)",
      "frequency_per_week": (số lần/tuần),
      "duration_minutes": (phút/lần),
      "intensity": "low/medium/high",
      "calories_per_session": (ước tính calo),
      "notes": "ghi chú"
    }}
  ],
  "nutrition_guidelines": {{
    "daily_calories": (calo/ngày),
    "macros": {{
      "protein_percent": (% protein),
      "carbs_percent": (% carbs),
      "fat_percent": (% fat)
    }},
    "meal_timing": ["breakfast", "lunch", "dinner", "snack"],
    "hydration_liters": (lít nước/ngày),
    "supplements": ["vitamin D", "..."]
  }},
  "risk_factors": ["rủi ro 1", "rủi ro 2"],
  "success_tips": ["mẹo 1", "mẹo 2"],
  "progress_indicators": ["chỉ số theo dõi 1", "chỉ số 2"]
}}

Chỉ trả về JSON, không có text khác.
""")
        
        # Chuẩn bị dữ liệu
        age = profile_data.get('age', 'chưa rõ')
        gender = profile_data.get('gender', 'chưa rõ')
        weight = profile_data.get('weight', 'chưa rõ')
        height = profile_data.get('height', 'chưa rõ')
        conditions = profile_data.get('conditions_text', 'Không có')
        
        activities_str = ', '.join(available_activities) if available_activities else 'Không có hạn chế'
        restrictions_str = ', '.join(dietary_restrictions) if dietary_restrictions else 'Không có hạn chế'
        
        # Gọi AI
        try:
            response = self.llm.invoke(prompt_template.format(
                age=age, gender=gender, weight=weight, height=height,
                conditions=conditions, goal_type=goal_type,
                target_value=target_value, target_unit=target_unit,
                duration_days=duration_days, activities=activities_str,
                restrictions=restrictions_str
            ))
            
            # Parse JSON response
            ai_analysis = json.loads(response.content.strip())
            
            # Validate và làm sạch dữ liệu
            if not isinstance(ai_analysis, dict):
                raise ValueError("Invalid AI response format")
            
            # Validate exercise recommendations sử dụng đúng activities (linh hoạt)
            exercise_recs = ai_analysis.get('exercise_recommendations', [])
            if exercise_recs and available_activities:
                # Kiểm tra xem AI có sử dụng đúng activities không
                ai_activities = [rec.get('activity', '') for rec in exercise_recs]
                
                # Kiểm tra linh hoạt - cho phép một số hoạt động không khớp
                valid_count = sum(1 for activity in ai_activities if activity in available_activities)
                total_count = len(ai_activities)
                
                # Nếu ít hơn 50% activities hợp lệ, thì sử dụng fallback
                if valid_count < total_count * 0.5:
                    print(f"Warning: AI không sử dụng đủ activities hợp lệ. Expected: {available_activities}, Got: {ai_activities}")
                    raise ValueError("AI không sử dụng đủ activities được chọn")
                
            return ai_analysis
            
        except Exception as e:
            # Fallback nếu AI lỗi
            return self._create_fallback_analysis(goal_type, target_value, duration_days, available_activities)
    
    def _create_fallback_analysis(self, goal_type: str, target_value: float, duration_days: int, available_activities: List[str] = None) -> Dict[str, Any]:
        """Tạo phân tích dự phòng khi AI lỗi"""
        
        weeks = max(1, duration_days // 7)
        
        # Tạo exercise recommendations từ available_activities
        exercise_recommendations = []
        if available_activities and len(available_activities) > 0:
            # Chia đều các hoạt động trong tuần
            activities_per_week = min(len(available_activities), 5)  # Tối đa 5 hoạt động/tuần
            for i, activity in enumerate(available_activities[:activities_per_week]):
                frequency = max(1, 7 // activities_per_week)  # Phân bố đều trong tuần
                exercise_recommendations.append({
                    "activity": activity,
                    "frequency_per_week": frequency,
                    "duration_minutes": 30,
                    "intensity": "medium",
                    "calories_per_session": 150,
                    "notes": f"Hoạt động {activity} theo kế hoạch"
                })
        else:
            # Fallback nếu không có activities
            exercise_recommendations = [
                {
                    "activity": "đi bộ",
                    "frequency_per_week": 5,
                    "duration_minutes": 30,
                    "intensity": "medium",
                    "calories_per_session": 150,
                    "notes": "Hoạt động cơ bản an toàn"
                }
            ]
        
        return {
            "feasibility_score": 7,
            "weekly_targets": [
                {
                    "week": i + 1,
                    "target_progress": min(100, (i + 1) * 100 / weeks),
                    "focus": f"Tuần {i + 1}: Duy trì đều đặn"
                }
                for i in range(weeks)
            ],
            "exercise_recommendations": exercise_recommendations,
            "nutrition_guidelines": {
                "daily_calories": 2000,
                "macros": {"protein_percent": 20, "carbs_percent": 50, "fat_percent": 30},
                "meal_timing": ["breakfast", "lunch", "dinner"],
                "hydration_liters": 2.5,
                "supplements": []
            },
            "risk_factors": ["Thiếu động lực", "Không tuân thủ kế hoạch"],
            "success_tips": ["Đặt mục tiêu nhỏ", "Theo dõi tiến độ hàng ngày"],
            "progress_indicators": ["Cân nặng", "Năng lượng", "Giấc ngủ"]
        }
    
    def _generate_detailed_schedule(
        self, 
        plan_id: int, 
        start_date: date, 
        duration_days: int, 
        ai_analysis: Dict[str, Any]
    ):
        """Tạo lịch trình chi tiết theo ngày"""
        
        logger.info(f"Starting detailed schedule generation for plan {plan_id}")
        exercise_recs = ai_analysis.get('exercise_recommendations', [])
        nutrition = ai_analysis.get('nutrition_guidelines', {})
        
        logger.info(f"Found {len(exercise_recs)} exercise recommendations")
        logger.info(f"Exercise recommendations: {[ex.get('activity', 'unknown') for ex in exercise_recs]}")
        
        # Tạo hoạt động theo tuần với phân bố đều
        # Tạo lịch trình cho từng hoạt động riêng biệt
        for i, exercise in enumerate(exercise_recs):
            frequency = exercise.get('frequency_per_week', 3)
            activity_name = exercise.get('activity', 'Tập luyện')
            
            logger.info(f"Processing exercise {i+1}: {activity_name} with frequency {frequency}/week")
            
            # Tạo danh sách ngày tập cho hoạt động này
            exercise_days = []
            for day_offset in range(duration_days):
                day_of_week = day_offset % 7
                
                # Phân bố hoạt động đều trong tuần
                if frequency >= 7:
                    # Tập hàng ngày
                    should_exercise = True
                elif frequency == 6:
                    # Tập 6 ngày, nghỉ 1 ngày (chủ nhật)
                    should_exercise = day_of_week < 6
                elif frequency == 5:
                    # Tập 5 ngày, nghỉ 2 ngày (thứ 7, chủ nhật)
                    should_exercise = day_of_week < 5
                elif frequency == 4:
                    # Tập 4 ngày: thứ 2, 4, 6, chủ nhật
                    should_exercise = day_of_week in [0, 2, 4, 6]
                elif frequency == 3:
                    # Tập 3 ngày: thứ 2, 4, 6
                    should_exercise = day_of_week in [0, 2, 4]
                elif frequency == 2:
                    # Tập 2 ngày: phân bố dựa trên index của exercise
                    if i % 3 == 0:
                        should_exercise = day_of_week in [0, 3]  # Thứ 2, 5
                    elif i % 3 == 1:
                        should_exercise = day_of_week in [1, 4]  # Thứ 3, 6
                    else:
                        should_exercise = day_of_week in [2, 5]  # Thứ 4, 7
                else:
                    # Tập 1 ngày: phân bố dựa trên index của exercise
                    target_day = i % 7  # Mỗi exercise có ngày khác nhau trong tuần
                    should_exercise = day_of_week == target_day
                
                if should_exercise:
                    exercise_days.append(day_offset)
            
            # Thêm hoạt động vào các ngày đã chọn
            if frequency == 1:
                target_day = i % 7
                day_names = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
                logger.info(f"Adding {activity_name} to {len(exercise_days)} days (target day: {day_names[target_day]})")
            else:
                logger.info(f"Adding {activity_name} to {len(exercise_days)} days")
            for day_offset in exercise_days:
                current_date = start_date + timedelta(days=day_offset)
                date_str = current_date.isoformat()
                
                try:
                    activity_id = db.add_plan_activity(
                        health_plan_id=plan_id,
                        date=date_str,
                        activity_type=exercise.get('activity', 'general'),
                        activity_name=activity_name,
                        duration_minutes=exercise.get('duration_minutes', 30),
                        intensity=exercise.get('intensity', 'medium'),
                        calories_target=exercise.get('calories_per_session'),
                        instructions=exercise.get('notes', '')
                    )
                    logger.debug(f"Added activity {activity_id} for {activity_name} on {date_str}")
                except Exception as e:
                    logger.error(f"Error adding activity {activity_name} on {date_str}: {str(e)}")
                    raise
        
        # Thêm bữa ăn hàng ngày cho tất cả các ngày
        logger.info("Adding meal plans")
        meal_timing = nutrition.get('meal_timing', ['breakfast', 'lunch', 'dinner'])
        daily_calories = nutrition.get('daily_calories', 2000)
        calories_per_meal = daily_calories / len(meal_timing)
        
        for day_offset in range(duration_days):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.isoformat()
            
            for meal_type in meal_timing:
                try:
                    meal_id = db.add_plan_meal(
                        health_plan_id=plan_id,
                        date=date_str,
                        meal_type=meal_type,
                        food_items=[{
                            "name": "Thực phẩm được khuyến nghị",
                            "amount": "khẩu phần vừa phải",
                            "calories": calories_per_meal,
                            "notes": "Tuân thủ hướng dẫn dinh dưỡng"
                        }],
                        total_calories=calories_per_meal,
                        macros=nutrition.get('macros', {}),
                        preparation_notes=f"Bữa {meal_type} theo kế hoạch"
                    )
                    logger.debug(f"Added meal {meal_id} for {meal_type} on {date_str}")
                except Exception as e:
                    logger.error(f"Error adding meal {meal_type} on {date_str}: {str(e)}")
                    raise
        
        logger.info(f"Completed detailed schedule generation for plan {plan_id}")
    
    def adjust_plan_based_on_feedback(
        self,
        plan_id: int,
        health_profile_id: int,
        actual_activities: List[Dict[str, Any]],
        actual_meals: List[Dict[str, Any]],
        target_date: date,
        adjustment_days: int = 7
    ) -> Dict[str, Any]:
        """
        Điều chỉnh kế hoạch dựa trên hoạt động thực tế
        
        Args:
            plan_id: ID kế hoạch
            health_profile_id: ID profile
            actual_activities: Hoạt động đã thực hiện
            actual_meals: Bữa ăn đã thực hiện  
            target_date: Ngày bắt đầu điều chỉnh
            adjustment_days: Số ngày điều chỉnh tiếp theo
        """
        
        # Lấy kế hoạch hiện tại
        plan = db.get_health_plan(plan_id, health_profile_id)
        if not plan:
            raise ValueError("Plan not found")
        
        # Phân tích độ lệch
        analysis = self._analyze_plan_deviation(plan, actual_activities, actual_meals)
        
        # Tạo kế hoạch điều chỉnh
        adjusted_schedule = self._create_adjusted_schedule(
            plan, analysis, target_date, adjustment_days
        )
        
        # Cập nhật database với lịch trình mới
        self._update_plan_schedule(plan_id, adjusted_schedule, target_date)
        
        return {
            "adjustment_analysis": analysis,
            "adjusted_schedule": adjusted_schedule,
            "message": "Kế hoạch đã được điều chỉnh dựa trên hoạt động thực tế"
        }
    
    def _analyze_plan_deviation(
        self,
        plan: Dict[str, Any],
        actual_activities: List[Dict[str, Any]],
        actual_meals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Phân tích độ lệch so với kế hoạch"""
        
        # Tính toán calories thực tế vs kế hoạch
        planned_calories = sum(meal.get('total_calories', 0) for meal in actual_meals if meal.get('is_completed'))
        actual_calories = sum(meal.get('total_calories', 0) for meal in actual_meals)
        
        # Tính toán hoạt động thực tế vs kế hoạch
        planned_exercise = len([a for a in actual_activities if not a.get('is_completed')])
        completed_exercise = len([a for a in actual_activities if a.get('is_completed')])
        
        return {
            "calorie_variance": actual_calories - planned_calories,
            "exercise_completion_rate": completed_exercise / max(1, len(actual_activities)) * 100,
            "needs_adjustment": abs(actual_calories - planned_calories) > planned_calories * 0.2 or 
                              completed_exercise / max(1, len(actual_activities)) < 0.7
        }
    
    def _create_adjusted_schedule(
        self,
        plan: Dict[str, Any],
        analysis: Dict[str, Any],
        start_date: date,
        days: int
    ) -> List[Dict[str, Any]]:
        """Tạo lịch trình điều chỉnh"""
        
        ai_analysis = plan.get('ai_analysis', {})
        
        # Tăng cường hoạt động nếu ăn nhiều hơn kế hoạch
        exercise_multiplier = 1.0
        if analysis.get('calorie_variance', 0) > 0:
            exercise_multiplier = 1.2
        elif analysis.get('exercise_completion_rate', 100) < 70:
            exercise_multiplier = 0.8  # Giảm bớt nếu không theo kịp
        
        schedule = []
        exercise_recs = ai_analysis.get('exercise_recommendations', [])
        
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            
            daily_activities = []
            for exercise in exercise_recs:
                frequency = exercise.get('frequency_per_week', 3)
                if day_offset % 7 < frequency:
                    daily_activities.append({
                        "activity_type": exercise.get('activity', 'general'),
                        "activity_name": exercise.get('activity', 'Tập luyện'),
                        "duration_minutes": int(exercise.get('duration_minutes', 30) * exercise_multiplier),
                        "intensity": exercise.get('intensity', 'medium'),
                        "calories_target": exercise.get('calories_per_session'),
                        "adjustment_reason": "Điều chỉnh dựa trên hoạt động trước đó"
                    })
            
            schedule.append({
                "date": current_date.isoformat(),
                "activities": daily_activities,
                "adjustment_notes": f"Ngày {day_offset + 1}: Điều chỉnh {exercise_multiplier:.1f}x"
            })
        
        return schedule
    
    def _update_plan_schedule(
        self,
        plan_id: int,
        schedule: List[Dict[str, Any]],
        start_date: date
    ):
        """Cập nhật lịch trình trong database"""
        
        for day_data in schedule:
            date_str = day_data['date']
            
            # Xóa hoạt động cũ cho ngày này (nếu chưa hoàn thành)
            with db.get_conn() as conn:
                conn.execute(
                    "DELETE FROM health_plan_activities WHERE health_plan_id = ? AND date = ? AND is_completed = 0",
                    (plan_id, date_str)
                )
            
            # Thêm hoạt động mới
            for activity in day_data['activities']:
                db.add_plan_activity(
                    health_plan_id=plan_id,
                    date=date_str,
                    activity_type=activity['activity_type'],
                    activity_name=activity['activity_name'],
                    duration_minutes=activity['duration_minutes'],
                    intensity=activity['intensity'],
                    calories_target=activity.get('calories_target'),
                    instructions=activity.get('adjustment_reason', '')
                )


# Singleton instance
health_planner_service = HealthPlannerService()
