Tôi sẽ giải thích chi tiết các kỹ thuật prompting và function calling được sử dụng trong project này:
Read file: app/api.py
## Kỹ thuật Prompting trong Project

### 1. **Role-Based Prompting (Định nghĩa vai trò)**
```python
"Bạn là chuyên gia tư vấn sức khỏe và dinh dưỡng"
```
- **Mục đích**: Thiết lập context và chuyên môn cho AI
- **Hiệu quả**: AI sẽ trả lời theo góc độ chuyên gia y tế

### 2. **Task-Oriented Instructions (Hướng dẫn nhiệm vụ cụ thể)**
```python
1. TƯ VẤN THỰC PHẨM:
   - Sử dụng kiến thức chuyên môn...
   - Đưa ra lời khuyên dựa trên tình trạng sức khỏe...
2. CẬP NHẬT THÔNG TIN SỨC KHỎE:
   - QUAN TRỌNG: Khi người dùng chia sẻ...
```
- **Kỹ thuật**: Chia nhỏ nhiệm vụ thành các mục rõ ràng
- **Lợi ích**: AI hiểu chính xác khi nào làm gì

### 3. **Few-Shot Learning với Examples**
```python
- Ví dụ function calls:
  * "Tôi 28 tuổi, cao 1m75, nặng 70kg" -> update_health_status({"age": 28, "new_height_cm": 175, "new_weight_kg": 70})
  * "Tôi bị tiểu đường type 2" -> update_health_status({"new_conditions": ["tiểu đường type 2"]})
```
- **Kỹ thuật**: Cung cấp ví dụ cụ thể input → output
- **Hiệu quả**: AI học pattern và áp dụng cho trường hợp tương tự

### 4. **Context Injection (Chèn thông tin ngữ cảnh)**
```python
THÔNG TIN NGƯỜI DÙNG:
- Hồ sơ: {profile_data.get('profile_name')}
- Tuổi: {profile_data.get('age')}
- Cân nặng hiện tại: {profile_data.get('weight')} kg
- Tình trạng sức khỏe: {profile_data.get('conditions_text')}
```
- **Kỹ thuật**: Dynamic context dựa trên dữ liệu user
- **Lợi ích**: AI có thông tin cá nhân để tư vấn chính xác

### 5. **Constraint-Based Prompting (Ràng buộc hành vi)**
```python
- Chỉ sử dụng function search_food_database khi gặp thực phẩm đặc thù/địa phương
- LUÔN gọi function update_health_status khi có thông tin sức khỏe
- Ưu tiên an toàn sức khỏe
```
- **Mục đích**: Kiểm soát khi nào AI gọi function
- **Hiệu quả**: Tránh gọi function không cần thiết

## Function Calling Architecture

### 1. **Tool Definition Schema**
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "update_health_status",
            "description": "Cập nhật hồ sơ sức khỏe khi người dùng chia sẻ thông tin về tuổi, cân nặng...",
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "description": "Tuổi của người dùng"},
                    "gender": {"type": "string", "enum": ["Nam", "Nữ", "Khác"]},
                    "new_weight_kg": {"type": "number", "description": "Cân nặng hiện tại theo kg"}
                },
                "required": []
            }
        }
    }
]
```
**Đặc điểm:**
- **Descriptive naming**: Tên function rõ nghĩa
- **Detailed parameters**: Mô tả chi tiết từng tham số
- **Flexible requirements**: `"required": []` cho linh hoạt
- **Vietnamese enum**: Sử dụng tiếng Việt cho dễ hiểu

### 2. **Tool Executor Pattern**
```python
def tool_executor(name: str, args: dict):
    if name == "search_food_database":
        # Thực thi logic tra cứu
        foods = db.search_food_by_name(args.get("food_name", ""))
        return {"name": food["name"], "category": food["category"], ...}
    
    elif name == "update_health_status":
        # Logic cập nhật phức tạp với validation
        # Gender mapping: "Nam" -> "male"
        # Weight delta vs absolute
        # JSON merge cho conditions
        db.update_health_profile(profile_id, current_user["id"], **update_data)
        return {"success": True, "updated_conditions": [...]}
```
**Kỹ thuật:**
- **Centralized dispatch**: Một function xử lý tất cả tools
- **Error handling**: Try/catch và fallback values
- **Data transformation**: Mapping Vietnamese → English
- **Complex logic**: Merge conditions, handle deltas

### 3. **Multi-Turn Function Calling Loop**
```python
def chat_with_food_tools(messages, tools, tool_executor, max_tool_loops=3):
    for _ in range(max_tool_loops):
        resp = client.chat.completions.create(
            model=model, messages=working_messages, tools=tools, tool_choice="auto"
        )
        
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return msg.content  # Kết thúc nếu không có tool calls
            
        # Thực thi tất cả tool calls
        for tc in tool_calls:
            result = tool_executor(tc.function.name, json.loads(tc.function.arguments))
            working_messages.append({
                "role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)
            })
```
**Đặc điểm:**
- **Iterative refinement**: AI có thể gọi nhiều tools liên tiếp
- **Context accumulation**: Kết quả tool được thêm vào conversation
- **Automatic termination**: Dừng khi AI không cần thêm tools

### 4. **Advanced Prompting Techniques**

#### **Conditional Function Calling**
```python
"Chỉ sử dụng function search_food_database khi gặp thực phẩm đặc thù/địa phương mà bạn không chắc chắn"
```
- **Logic**: AI ưu tiên kiến thức có sẵn, chỉ query DB khi cần
- **Hiệu quả**: Giảm unnecessary API calls

#### **Mandatory Function Calling**
```python
"QUAN TRỌNG: Khi người dùng chia sẻ bất kỳ thông tin cá nhân nào về sức khỏe, hãy LUÔN gọi function update_health_status"
```
- **Keyword**: "QUAN TRỌNG", "LUÔN" để nhấn mạnh
- **Trigger patterns**: Liệt kê rõ các trường hợp trigger

#### **Multi-Parameter Function Calls**
```python
"Tôi 28 tuổi, cao 1m75, nặng 70kg" 
→ update_health_status({"age": 28, "new_height_cm": 175, "new_weight_kg": 70})
```
- **Information extraction**: AI tự động parse nhiều thông tin từ 1 câu
- **Atomic updates**: Gom nhiều field update trong 1 function call

### 5. **Error Handling & Fallbacks**
```python
# Tool executor error handling
try:
    conditions_data = json.loads(current_conditions)
    if not isinstance(conditions_data, dict):
        conditions_data = {"conditions_list": []}
except Exception:
    conditions_data = {"conditions_list": []}

# AI fallback
except Exception as e:
    if "AZURE_OPENAI_ENDPOINT" not in os.environ:
        ai_response = "Xin lỗi, tính năng AI chưa được cấu hình..."
        return {"ai_response": ai_response}
```

## Kết luận

Project này sử dụng **sophisticated prompting** kết hợp **intelligent function calling** để tạo ra một hệ thống AI có thể:

1. **Tự động nhận diện** khi nào cần cập nhật thông tin sức khỏe
2. **Chính xác trích xuất** nhiều thông tin từ ngôn ngữ tự nhiên
3. **Linh hoạt xử lý** các trường hợp edge case (weight delta, gender mapping)
4. **Tối ưu performance** bằng cách chỉ query DB khi cần thiết
5. **Đảm bảo data integrity** thông qua validation và error handling

Đây là một ví dụ điển hình của **agentic AI system** với khả năng reasoning và action execution.