import json
from typing import Any, Dict, List

from . import db


def tools_spec() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "lookup_food",
                "description": "Tra cứu thông tin thực phẩm trong cơ sở dữ liệu nội bộ theo tên.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Tên thực phẩm cần tra cứu"},
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def execute_tool_call(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "lookup_food":
        query = (args.get("name") or "").strip()
        if not query:
            return {"ok": False, "error": "Thiếu tên thực phẩm"}
        items = db.search_food_by_name(query)
        return {"ok": True, "query": query, "results": items}
    return {"ok": False, "error": f"Tool không hỗ trợ: {name}"}


