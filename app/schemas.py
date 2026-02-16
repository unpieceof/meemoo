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
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "memo_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["memo_id", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["recommendations"],
    "additionalProperties": False,
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
}
