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
                    "category": {"type": "string"},
                    "emoji": {"type": "string"},
                    "one_liner": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "memo_id": {"type": "string"},
                                "title": {"type": "string"},
                                "preview": {"type": "string"},
                                "hook": {"type": "string"},
                                "reason": {"type": "string"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["memo_id", "title", "preview", "hook", "reason", "tags"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["category", "emoji", "one_liner", "items"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["categories"],
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
    "sms": "sms",
    "help": "help",
    "start": "help",
}
