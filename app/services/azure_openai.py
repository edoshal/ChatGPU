import base64
import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI


load_dotenv()


def get_client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    if not endpoint or not api_key:
        raise RuntimeError("Thiếu AZURE_OPENAI_ENDPOINT hoặc AZURE_OPENAI_API_KEY trong .env")
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    return client


def get_chat_model_name() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def standardize_conditions(free_text: str) -> Dict[str, Any]:
    """Dùng LLM để chuẩn hoá bệnh lý thành JSON ngắn gọn."""
    client = get_client()
    model = get_chat_model_name()
    system = (
        "Bạn là trợ lý y tế. Hãy chuẩn hoá thông tin bệnh lý từ người dùng thành JSON ngắn gọn:\n"
        "- keys: conditions (list), allergies (list), medications (list), notes (string).\n"
        "- Không thêm diễn giải dư thừa.\n"
    )
    user = f"Thông tin bệnh lý gốc (tiếng Việt tự nhiên):\n{free_text}\n\nTrả về JSON duy nhất."
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except Exception:
        return {"conditions": [], "allergies": [], "medications": [], "notes": content}


def summarize_medical_text(text: str) -> str:
    client = get_client()
    model = get_chat_model_name()
    system = (
        "Bạn là trợ lý y tế. Hãy tóm tắt và biên soạn hồ sơ khám sức khoẻ dưới dạng gạch đầu dòng rõ ràng,"
        " ưu tiên chẩn đoán, kết quả xét nghiệm bất thường, và khuyến nghị."
    )
    user = f"Văn bản hồ sơ (đã trích xuất từ PDF):\n{text}\n\nYêu cầu: tóm tắt rõ ràng, ngắn gọn."
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def to_image_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def chat_with_food_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_executor,
    max_tool_loops: int = 3,
) -> str:
    """
    Vòng lặp function calling: gọi model, nếu có tool_calls thì thực thi rồi feed-back vào cuộc hội thoại.
    tool_executor(name: str, args: Dict) -> Dict hoặc str (sẽ stringify).
    """
    client = get_client()
    model = get_chat_model_name()
    working_messages = list(messages)

    for _ in range(max_tool_loops):
        resp = client.chat.completions.create(
            model=model,
            messages=working_messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2,
        )
        msg = resp.choices[0].message

        # Nếu không có tool calls → trả lời cuối
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return msg.content or ""

        # Thực thi từng tool call và append kết quả
        working_messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in tool_calls]})
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            result = tool_executor(name, args)
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)
            working_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": result,
                }
            )

    # Nếu quá số vòng, gọi thêm lần cuối không tool
    final = client.chat.completions.create(
        model=model,
        messages=working_messages,
        temperature=0.2,
    )
    return final.choices[0].message.content or ""


