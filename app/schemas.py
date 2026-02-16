"""JSON schemas for agent outputs."""

ANALYST_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "bullets": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 3,
        },
        "category": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "bullets", "category", "tags"],
    "additionalProperties": False,
}

RECOMMENDER_SCHEMA = {
    "type": "object",
    "properties": {
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},      # 예: "배움", "정보" 또는 모델이 재가공한 카테고리명
                    "emoji": {"type": "string"},
                    "one_liner": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "memo_id": {"type": "string"},
                                "title": {"type": "string"},
                                "preview": {"type": "string"},  # summary_bullets에서 한 줄 뽑기
                                "hook": {"type": "string"},     # 자극적 한 줄
                                "reason": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "confidence": {"type": "number"}
                            },
                            "required": ["memo_id", "title", "preview", "hook", "reason"]
                        }
                    }
                },
                "required": ["category", "emoji", "one_liner", "items"]
            }
        }
    },
    "required": ["categories"]
}


ROUTE_COMMANDS = {
    "save": "analyst",
    "list": "librarian",
    "search": "librarian",
    "category": "librarian",
    "view": "librarian",
    "delete": "librarian",
    "recommend": "recommender",
    "verbose": "setting",
    "help": "help",
    "start": "help",
}
