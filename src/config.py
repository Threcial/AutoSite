import os
from dotenv import load_dotenv

load_dotenv()


def _str_to_bool(val):
    return val.lower() in ("true", "1", "yes") if val else True


class Config:
    def __init__(self):
        self.base_url = self._get_url("WP_BASE_URL")
        self.username = os.getenv("WP_USERNAME", "")
        self.app_password = os.getenv("WP_APP_PASSWORD", "")
        self.default_author = int(os.getenv("WP_DEFAULT_AUTHOR", "1"))
        self.default_status = os.getenv("WP_DEFAULT_STATUS", "draft")
        self.verify_ssl = _str_to_bool(os.getenv("WP_VERIFY_SSL", "true"))

    def _get_url(self, key):
        val = os.getenv(key, "").rstrip("/")
        return val

    def validate(self):
        missing = []
        if not self.base_url:
            missing.append("WP_BASE_URL")
        if not self.username:
            missing.append("WP_USERNAME")
        if not self.app_password:
            missing.append("WP_APP_PASSWORD")
        if missing:
            print("[ERROR] Missing required environment variables:")
            for key in missing:
                print(f"        {key}")
            print("[HINT]  Copy .env.example to .env and fill in the values.")
            return False
        return True
