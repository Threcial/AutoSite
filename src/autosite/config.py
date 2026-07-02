import os
import sys

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_CONFIG_PATH = "config.yaml"
EXAMPLE_CONFIG_PATH = "config.example.yaml"

STANDARD_FRONTMATTER_FIELDS = [
    "title", "slug", "wp_post_id", "wp_link", "status",
    "categories", "tags", "author", "excerpt", "cover",
    "date", "last_published_at", "last_updated_at", "last_uploaded_at",
]


class Config:
    def __init__(self, path=None):
        self.path = path or DEFAULT_CONFIG_PATH
        self._data = {}
        self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            print(f"[ERROR] Config file not found: {self.path}")
            if os.path.isfile(EXAMPLE_CONFIG_PATH):
                print(f"[HINT]  Copy {EXAMPLE_CONFIG_PATH} to {self.path} and fill in the values.")
            sys.exit(1)

        if yaml is None:
            print("[ERROR] PyYAML is not installed. Run: pip install PyYAML")
            sys.exit(1)

        with open(self.path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def _get(self, *keys, default=None):
        d = self._data
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return default
        return d if d is not None else default

    @property
    def site_name(self):
        return self._get("site", "name", default="")

    @property
    def base_url(self):
        return self._get("site", "base_url", default="").rstrip("/")

    @property
    def api_base(self):
        return self._get("site", "api_base", default="").rstrip("/")

    @property
    def username(self):
        return self._get("site", "username", default="")

    @property
    def application_password(self):
        return self._get("site", "application_password", default="")

    @property
    def verify_ssl(self):
        return self._get("site", "verify_ssl", default=True)

    @property
    def timeout(self):
        return self._get("site", "timeout", default=30)

    @property
    def default_status(self):
        return self._get("defaults", "status", default="draft")

    @property
    def default_author(self):
        return self._get("defaults", "author", default=1)

    @property
    def default_categories(self):
        return self._get("defaults", "categories", default=[])

    @property
    def default_tags(self):
        return self._get("defaults", "tags", default=[])

    @property
    def default_excerpt(self):
        return self._get("defaults", "excerpt", default="")

    @property
    def auto_create_categories(self):
        return self._get("defaults", "auto_create_categories", default=False)

    @property
    def auto_create_tags(self):
        return self._get("defaults", "auto_create_tags", default=True)

    @property
    def write_back(self):
        return self._get("upload", "write_back", default=True)

    @property
    def backup_before_write(self):
        return self._get("upload", "backup_before_write", default=True)

    @property
    def standardize_frontmatter(self):
        return self._get("upload", "standardize_frontmatter", default=True)

    @property
    def title_match_enabled(self):
        return self._get("upload", "title_match_enabled", default=True)

    @property
    def title_match_strict(self):
        return self._get("upload", "title_match_strict", default=True)

    @property
    def allow_publish_status(self):
        return self._get("upload", "allow_publish_status", default=False)

    @property
    def update_detection_order(self):
        return self._get("upload", "update_detection_order",
                         default=["wp_post_id", "slug", "state", "title_exact_match"])

    @property
    def convert_to_html(self):
        return self._get("markdown", "convert_to_html", default=True)

    @property
    def first_h1_as_title(self):
        return self._get("markdown", "first_h1_as_title", default=True)

    @property
    def remove_first_h1_from_content(self):
        return self._get("markdown", "remove_first_h1_from_content", default=False)

    @property
    def markdown_extensions(self):
        return self._get("markdown", "extensions",
                         default=["extra", "tables", "fenced_code", "codehilite", "toc", "sane_lists"])

    @property
    def notification_enabled(self):
        return self._get("notification", "enabled", default=True)

    @property
    def success_popup(self):
        return self._get("notification", "success_popup", default=True)

    @property
    def error_popup(self):
        return self._get("notification", "error_popup", default=True)

    @property
    def history_file(self):
        return self._get("logs", "history_file", default="logs/upload-history.jsonl")

    @property
    def latest_file(self):
        return self._get("logs", "latest_file", default="logs/upload-latest.json")

    @property
    def state_file(self):
        return self._get("state", "file", default="state/state.json")
