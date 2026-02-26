import json
import os

from Jarvis.config import config


class TelegramStateStore:
    def __init__(self):
        path = getattr(config, "telegram_state_path", "") or ""
        if not path:
            path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "telegram_state.json")
            )
        self.path = path

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self, data):
        folder = os.path.dirname(self.path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_primary_chat_id(self):
        data = self._load()
        chat_id = data.get("primary_chat_id")
        if chat_id not in ("", None):
            return chat_id
        # Fallback to security allowlist user id when DM history exists but local
        # state file has not been initialized yet.
        raw_ids = getattr(config, "security_allowed_telegram_user_ids", "") or ""
        ids = [x.strip() for x in str(raw_ids).split(",") if x.strip()]
        if ids:
            first = ids[0]
            try:
                return int(first)
            except Exception:
                return first
        return None

    def set_primary_chat_id(self, chat_id):
        if chat_id in ("", None):
            return False
        data = self._load()
        data["primary_chat_id"] = chat_id
        return self._save(data)

    def get_last_message_id(self, chat_id=None):
        data = self._load()
        if chat_id is None:
            chat_id = data.get("primary_chat_id")
        if chat_id in ("", None):
            return None
        per_chat = data.get("per_chat") or {}
        row = per_chat.get(str(chat_id)) or {}
        return row.get("last_message_id")

    def set_last_message_id(self, chat_id, message_id):
        if chat_id in ("", None) or message_id in ("", None):
            return False
        data = self._load()
        per_chat = data.get("per_chat")
        if not isinstance(per_chat, dict):
            per_chat = {}
        row = per_chat.get(str(chat_id))
        if not isinstance(row, dict):
            row = {}
        row["last_message_id"] = message_id
        per_chat[str(chat_id)] = row
        data["per_chat"] = per_chat
        if "primary_chat_id" not in data:
            data["primary_chat_id"] = chat_id
        return self._save(data)

    def update_from_send_message_result(self, payload):
        if not isinstance(payload, dict):
            return False
        result = payload.get("result")
        if not isinstance(result, dict):
            return False
        chat = result.get("chat")
        if not isinstance(chat, dict):
            return False
        chat_id = chat.get("id")
        message_id = result.get("message_id")
        ok1 = self.set_primary_chat_id(chat_id)
        ok2 = self.set_last_message_id(chat_id, message_id)
        return bool(ok1 or ok2)

    def update_from_updates_result(self, payload):
        if not isinstance(payload, dict):
            return False
        items = payload.get("result")
        if not isinstance(items, list):
            return False
        chosen_chat_id = None
        for item in reversed(items):
            if not isinstance(item, dict):
                continue
            msg = item.get("message")
            if not isinstance(msg, dict):
                continue
            chat = msg.get("chat")
            if not isinstance(chat, dict):
                continue
            if str(chat.get("type", "")).lower() != "private":
                continue
            chosen_chat_id = chat.get("id")
            message_id = msg.get("message_id")
            self.set_last_message_id(chosen_chat_id, message_id)
            break
        if chosen_chat_id in ("", None):
            return False
        return self.set_primary_chat_id(chosen_chat_id)
