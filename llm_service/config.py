# config.py
MODEL_BACKEND = "claude"        # "claude" | "gemini" | "local"
LOCAL_MODEL_ENDPOINT = None
LOCAL_MODEL_NAME = None

TIER_MAP = {
    "claude": "standard",
    "gemini": "standard",
    "local":  "compact",
}
