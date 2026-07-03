import os
import sys
import json
import shutil
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import yaml

from .config import Config, DEFAULT_CONFIG_PATH, EXAMPLE_CONFIG_PATH
from .wordpress_client import WordPressClient
from .uploader import Uploader
from .context_menu import install as ctx_install, uninstall as ctx_uninstall, is_installed as ctx_is_installed


VALID_DETECTION_KEYS = {"wp_post_id", "slug", "state", "title_exact_match"}
STATUS_OPTIONS = ["draft", "publish", "private", "pending", "future"]


class AutoSiteConfigApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AutoSite 配置工具")
        self.root.geometry("900x650")
        self.root.minsize(800, 580)

        self._config_path = DEFAULT_CONFIG_PATH
        self._data = {}
        self._modified = False

        self._ensure_config()
        self._load_data()

        self._build_ui()
        self._populate_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ init helpers

    def _ensure_config(self):
        if os.path.isfile(self._config_path):
            return
        if not os.path.isfile(EXAMPLE_CONFIG_PATH):
            messagebox.showerror("错误", f"找不到 {self._config_path} 和 {EXAMPLE_CONFIG_PATH}。\n请先创建配置文件。")
            sys.exit(1)
        ok = messagebox.askyesno("配置文件不存在", f"config.yaml 不存在，是否从 config.example.yaml 复制生成？")
        if ok:
            shutil.copy2(EXAMPLE_CONFIG_PATH, self._config_path)
            messagebox.showinfo("已创建", f"已复制 {EXAMPLE_CONFIG_PATH} → {self._config_path}\n请填写配置后保存。")
        else:
            sys.exit(1)

    def _load_data(self):
        with open(self._config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def _save_data(self):
        bak = self._config_path + ".bak"
        try:
            shutil.copy2(self._config_path, bak)
        except Exception:
            pass
        content = yaml.dump(self._data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(self._config_path)),
                                   prefix=".config_tmp_", suffix=".yaml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            shutil.move(tmp, self._config_path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _on_close(self):
        if self._modified:
            if not messagebox.askyesno("未保存", "配置有未保存修改，是否退出？"):
                return
        self.root.destroy()

    # ------------------------------------------------------------------ build UI

    def _build_ui(self):
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        self._tab_site = ttk.Frame(self._notebook)
        self._tab_defaults = ttk.Frame(self._notebook)
        self._tab_upload = ttk.Frame(self._notebook)
        self._tab_markdown = ttk.Frame(self._notebook)
        self._tab_notification = ttk.Frame(self._notebook)
        self._tab_context_menu = ttk.Frame(self._notebook)
        self._tab_tools = ttk.Frame(self._notebook)

        self._notebook.add(self._tab_site, text="站点配置")
        self._notebook.add(self._tab_defaults, text="默认文章配置")
        self._notebook.add(self._tab_upload, text="上传行为")
        self._notebook.add(self._tab_markdown, text="Markdown 设置")
        self._notebook.add(self._tab_notification, text="通知与日志")
        self._notebook.add(self._tab_context_menu, text="右键菜单")
        self._notebook.add(self._tab_tools, text="工具")

        self._build_site_tab()
        self._build_defaults_tab()
        self._build_upload_tab()
        self._build_markdown_tab()
        self._build_notification_tab()
        self._build_context_menu_tab()
        self._build_tools_tab()
        self._build_bottom_bar()

    def _entry(self, parent, label, row, column=0, width=50, show=None, span=3):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 4), pady=2)
        var = tk.StringVar()
        kw = {"textvariable": var, "width": width}
        if show:
            kw["show"] = show
        w = ttk.Entry(parent, **kw)
        w.grid(row=row, column=column + 1, columnspan=span, sticky="ew", pady=2)
        return var, w

    def _check(self, parent, label, row, column=0, span=4):
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(parent, text=label, variable=var)
        cb.grid(row=row, column=column, columnspan=span, sticky="w", pady=2)
        return var, cb

    def _combo(self, parent, label, row, values, column=0, width=30, span=3):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 4), pady=2)
        var = tk.StringVar()
        w = ttk.Combobox(parent, textvariable=var, values=values, width=width, state="readonly")
        w.grid(row=row, column=column + 1, columnspan=span, sticky="w", pady=2)
        return var, w

    def _textbox(self, parent, label, row, height=4, width=60, span=4):
        f = ttk.LabelFrame(parent, text=label)
        f.grid(row=row, column=0, columnspan=span, sticky="nsew", pady=4, padx=2)
        txt = tk.Text(f, height=height, width=width, wrap="none")
        txt.pack(fill="both", expand=True, padx=4, pady=4)
        sb = ttk.Scrollbar(f, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)
        return txt

    # ------------------------------------------------------------ site tab

    def _build_site_tab(self):
        f = self._tab_site
        f.columnconfigure(1, weight=1)

        self.site_name_var, _ = self._entry(f, "站点名称", 0)
        self.site_url_var, _ = self._entry(f, "站点地址 base_url", 1)
        self.api_base_var, _ = self._entry(f, "API 地址 api_base", 2)
        self.username_var, _ = self._entry(f, "用户名 username", 3)
        self.password_var, self.password_entry = self._entry(f, "应用程序密码", 4, show="*")
        self._password_visible = False

        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=4, column=2, sticky="w", pady=2)
        self._btn_toggle_pw = ttk.Button(btn_frame, text="显示密码", command=self._toggle_password)
        self._btn_toggle_pw.pack(side="left", padx=2)

        self.ssl_var, _ = self._check(f, "验证 SSL verify_ssl", 5)
        self.timeout_var, _ = self._entry(f, "请求超时 timeout", 6, width=10, span=1)

        test_btn = ttk.Button(f, text="测试连接", command=self._test_connection)
        test_btn.grid(row=7, column=0, columnspan=4, pady=8)

        self._site_result = tk.Text(f, height=5, width=80, state="disabled", wrap="word")
        self._site_result.grid(row=8, column=0, columnspan=4, sticky="nsew", pady=4)
        f.rowconfigure(8, weight=1)

    def _toggle_password(self):
        self._password_visible = not self._password_visible
        self.password_entry.configure(show="" if self._password_visible else "*")
        self._btn_toggle_pw.configure(text="隐藏密码" if self._password_visible else "显示密码")

    # -------------------------------------------------------- defaults tab

    def _build_defaults_tab(self):
        f = self._tab_defaults
        f.columnconfigure(1, weight=1)

        self.default_status_var, _ = self._combo(f, "默认状态 status", 0, STATUS_OPTIONS)
        self.default_author_var, _ = self._entry(f, "默认作者 ID author", 1, width=10, span=1)
        self.default_excerpt_var, _ = self._entry(f, "默认摘要 excerpt", 2)

        self.categories_txt = self._textbox(f, "默认分类 categories（一行一个）", 3, height=4)
        self.tags_txt = self._textbox(f, "默认标签 tags（一行一个）", 4, height=4)

        self.auto_cat_var, _ = self._check(f, "自动创建分类 auto_create_categories", 5)
        self.auto_tag_var, _ = self._check(f, "自动创建标签 auto_create_tags", 6)

        self._status_warn = ttk.Label(f, text="", foreground="red", wraplength=500)
        self._status_warn.grid(row=7, column=0, columnspan=4, sticky="w", pady=2)

        self.default_status_var.trace_add("write", lambda *a: self._check_status_warning())

    def _check_status_warning(self):
        if self.default_status_var.get() == "publish":
            allow = self.allow_publish_var.get() if hasattr(self, "allow_publish_var") else False
            if not allow:
                self._status_warn.configure(text="当前配置不允许直接发布，实际上传时会降级为 draft")
            else:
                self._status_warn.configure(text="")
        else:
            self._status_warn.configure(text="")

    # --------------------------------------------------------- upload tab

    def _build_upload_tab(self):
        f = self._tab_upload
        f.columnconfigure(1, weight=1)

        self.write_back_var, _ = self._check(f, "上传后写回 Markdown write_back", 0)
        self.backup_var, _ = self._check(f, "写回前备份 backup_before_write", 1)
        self.standardize_var, _ = self._check(f, "标准化 Front Matter standardize_frontmatter", 2)
        self.title_match_var, _ = self._check(f, "允许标题匹配 title_match_enabled", 3)
        self.title_strict_var, _ = self._check(f, "标题严格匹配 title_match_strict", 4)
        self.allow_publish_var, _ = self._check(f, "允许直接发布 publish allow_publish_status", 5)

        self._publish_warn = ttk.Label(f, text="开启后，Markdown 中 status: publish 会直接发布到网站", foreground="red", wraplength=500)
        self._publish_warn.grid(row=6, column=0, columnspan=4, sticky="w", padx=(20, 0), pady=(0, 4))

        self.allow_publish_var.trace_add("write", lambda *a: self._check_publish_warning())

        self.detection_txt = self._textbox(f, "更新检测顺序 update_detection_order（一行一个）", 7, height=6)
        hint = ttk.Label(f, text="合法值: wp_post_id, slug, state, title_exact_match", foreground="gray")
        hint.grid(row=8, column=0, columnspan=4, sticky="w", padx=6)

    def _check_publish_warning(self):
        if self.allow_publish_var.get():
            self._publish_warn.configure(text="")
        else:
            self._publish_warn.configure(text="开启后，Markdown 中 status: publish 会直接发布到网站")

    # ------------------------------------------------------- markdown tab

    def _build_markdown_tab(self):
        f = self._tab_markdown
        f.columnconfigure(1, weight=1)

        self.md_convert_var, _ = self._check(f, "Markdown 转 HTML convert_to_html", 0)
        self.md_h1_title_var, _ = self._check(f, "第一个 H1 作为标题 first_h1_as_title", 1)
        self.md_remove_h1_var, _ = self._check(f, "从正文中移除第一个 H1 remove_first_h1_from_content", 2)

        self.extensions_txt = self._textbox(f, "Markdown 扩展 extensions（一行一个）", 3, height=6)
        hint = ttk.Label(f, text="常用扩展: extra, tables, fenced_code, codehilite, toc, sane_lists", foreground="gray")
        hint.grid(row=4, column=0, columnspan=4, sticky="w", padx=6)

    # --------------------------------------------------- notification tab

    def _build_notification_tab(self):
        f = self._tab_notification
        f.columnconfigure(1, weight=1)

        self.notify_enabled_var, _ = self._check(f, "启用通知 enabled", 0)
        self.notify_success_var, _ = self._check(f, "成功时弹窗 success_popup", 1)
        self.notify_error_var, _ = self._check(f, "失败时弹窗 error_popup", 2)

        self.history_file_var, _ = self._entry(f, "历史日志路径 history_file", 3)
        self.latest_file_var, _ = self._entry(f, "最新结果路径 latest_file", 4)
        self.state_file_var, _ = self._entry(f, "状态文件路径 state.file", 5)

        btn_f = ttk.LabelFrame(f, text="快速打开")
        btn_f.grid(row=6, column=0, columnspan=4, sticky="ew", pady=8, padx=2)

        for i, (txt, attr) in enumerate([
            ("打开历史日志", "history_file"),
            ("打开最新结果", "latest_file"),
            ("打开 state 文件", "state_file"),
        ]):
            b = ttk.Button(btn_f, text=txt, command=lambda a=attr: self._open_file(a))
            b.pack(side="left", padx=4, pady=4)

        ttk.Button(btn_f, text="打开 logs 目录", command=lambda: self._open_dir("logs")).pack(side="left", padx=4)
        ttk.Button(btn_f, text="打开 state 目录", command=lambda: self._open_dir("state")).pack(side="left", padx=4)

    def _open_file(self, attr):
        path = getattr(self, attr + "_var", None)
        if path:
            p = path.get().strip()
        else:
            p = ""
        if not p:
            messagebox.showinfo("提示", "路径为空")
            return
        absp = os.path.abspath(p)
        if not os.path.isfile(absp):
            messagebox.showinfo("提示", f"文件不存在：{absp}")
            return
        os.startfile(absp)

    def _open_dir(self, name):
        absp = os.path.abspath(name)
        if not os.path.isdir(absp):
            os.makedirs(absp, exist_ok=True)
        os.startfile(absp)

    # ---------------------------------------------------- context menu tab

    def _build_context_menu_tab(self):
        f = self._tab_context_menu

        self._ctx_status_label = ttk.Label(f, text="检查中…", font=("", 11))
        self._ctx_status_label.pack(pady=(20, 10))

        def install_ctx():
            ok, msg = ctx_install()
            if ok:
                messagebox.showinfo("成功", "右键菜单已安装。请重新打开资源管理器窗口后测试。")
            else:
                messagebox.showerror("失败", msg)
            self._refresh_ctx_status()

        def uninstall_ctx():
            ok, msg = ctx_uninstall()
            if ok:
                messagebox.showinfo("成功", "右键菜单已卸载。")
            else:
                messagebox.showerror("失败", msg)
            self._refresh_ctx_status()

        def refresh():
            self._refresh_ctx_status()

        btn_f = ttk.Frame(f)
        btn_f.pack(pady=10)
        ttk.Button(btn_f, text="安装右键菜单", command=install_ctx, width=20).pack(side="left", padx=6)
        ttk.Button(btn_f, text="卸载右键菜单", command=uninstall_ctx, width=20).pack(side="left", padx=6)
        ttk.Button(btn_f, text="检查右键菜单状态", command=refresh, width=20).pack(side="left", padx=6)

        info = ttk.Label(f, text="注册表路径（HKCU，无需管理员）：\nSoftware\\Classes\\SystemFileAssociations\\.md\\shell\\UploadToThrecial",
                         foreground="gray", justify="left")
        info.pack(pady=(20, 0))

        self._refresh_ctx_status()

    def _refresh_ctx_status(self):
        if ctx_is_installed():
            self._ctx_status_label.configure(text="✓ 已安装", foreground="green")
        else:
            self._ctx_status_label.configure(text="✗ 未安装", foreground="red")

    # --------------------------------------------------------- tools tab

    def _build_tools_tab(self):
        f = self._tab_tools
        f.columnconfigure(0, weight=1)

        ttk.Button(f, text="测试 WordPress 连接", command=self._test_connection, width=40).grid(row=0, column=0, pady=6)
        ttk.Button(f, text="选择 Markdown 文件测试 dry-run", command=self._run_dry_run, width=40).grid(row=1, column=0, pady=6)
        ttk.Button(f, text="打开 config.yaml", command=self._open_config, width=40).grid(row=2, column=0, pady=6)
        ttk.Button(f, text="打开项目目录", command=self._open_project_dir, width=40).grid(row=3, column=0, pady=6)
        ttk.Button(f, text="打开 README", command=self._open_readme, width=40).grid(row=4, column=0, pady=6)

        self._dry_run_result = tk.Text(f, height=12, width=90, state="disabled", wrap="word")
        self._dry_run_result.grid(row=5, column=0, sticky="nsew", pady=8)
        f.rowconfigure(5, weight=1)

    def _open_config(self):
        p = os.path.abspath(self._config_path)
        if os.path.isfile(p):
            os.startfile(p)
        else:
            messagebox.showinfo("提示", f"文件不存在：{p}")

    def _open_project_dir(self):
        os.startfile(os.path.abspath("."))

    def _open_readme(self):
        p = os.path.abspath("README.md")
        if os.path.isfile(p):
            os.startfile(p)
        else:
            messagebox.showinfo("提示", "README.md 不存在")

    # --------------------------------------------------------- bottom bar

    def _build_bottom_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=(4, 8))

        ttk.Button(bar, text="保存配置", command=self._save, width=14).pack(side="left", padx=2)
        ttk.Button(bar, text="重新加载配置", command=self._reload, width=14).pack(side="left", padx=2)
        ttk.Button(bar, text="测试连接", command=self._test_connection, width=14).pack(side="left", padx=2)
        ttk.Button(bar, text="退出", command=self._on_close, width=14).pack(side="right", padx=2)

    # ---------------------------------------------------------- populate

    def _populate_ui(self):
        d = self._data

        # site
        site = d.get("site", {})
        self._set(self.site_name_var, site.get("name", ""))
        self._set(self.site_url_var, site.get("base_url", ""))
        self._set(self.api_base_var, site.get("api_base", ""))
        self._set(self.username_var, site.get("username", ""))
        self._set(self.password_var, site.get("application_password", ""))
        self._set(self.ssl_var, site.get("verify_ssl", True))
        self._set(self.timeout_var, str(site.get("timeout", 30)))

        # defaults
        defaults = d.get("defaults", {})
        self._set(self.default_status_var, defaults.get("status", "draft"))
        self._set(self.default_author_var, str(defaults.get("author", 1)))
        self._set(self.default_excerpt_var, defaults.get("excerpt", ""))
        self._set_list(self.categories_txt, defaults.get("categories", []))
        self._set_list(self.tags_txt, defaults.get("tags", []))
        self._set(self.auto_cat_var, defaults.get("auto_create_categories", False))
        self._set(self.auto_tag_var, defaults.get("auto_create_tags", True))

        # upload
        upload = d.get("upload", {})
        self._set(self.write_back_var, upload.get("write_back", True))
        self._set(self.backup_var, upload.get("backup_before_write", True))
        self._set(self.standardize_var, upload.get("standardize_frontmatter", True))
        self._set(self.title_match_var, upload.get("title_match_enabled", True))
        self._set(self.title_strict_var, upload.get("title_match_strict", True))
        self._set(self.allow_publish_var, upload.get("allow_publish_status", False))
        self._set_list(self.detection_txt, upload.get("update_detection_order",
                                                       ["wp_post_id", "slug", "state", "title_exact_match"]))

        # markdown
        md = d.get("markdown", {})
        self._set(self.md_convert_var, md.get("convert_to_html", True))
        self._set(self.md_h1_title_var, md.get("first_h1_as_title", True))
        self._set(self.md_remove_h1_var, md.get("remove_first_h1_from_content", False))
        self._set_list(self.extensions_txt, md.get("extensions",
                                                     ["extra", "tables", "fenced_code", "codehilite", "toc", "sane_lists"]))

        # notification & logs
        notif = d.get("notification", {})
        self._set(self.notify_enabled_var, notif.get("enabled", True))
        self._set(self.notify_success_var, notif.get("success_popup", True))
        self._set(self.notify_error_var, notif.get("error_popup", True))

        logs = d.get("logs", {})
        self._set(self.history_file_var, logs.get("history_file", "logs/upload-history.jsonl"))
        self._set(self.latest_file_var, logs.get("latest_file", "logs/upload-latest.json"))

        state_cfg = d.get("state", {})
        self._set(self.state_file_var, state_cfg.get("file", "state/state.json"))

        self._modified = False

    @staticmethod
    def _set(var, value):
        if isinstance(var, tk.BooleanVar):
            var.set(bool(value))
        else:
            var.set(str(value) if value is not None else "")

    @staticmethod
    def _set_list(txt, items):
        txt.delete("1.0", "end")
        if items:
            txt.insert("1.0", "\n".join(str(x) for x in items))

    def _get_list(self, txt):
        raw = txt.get("1.0", "end").strip()
        if not raw:
            return []
        return [line.strip() for line in raw.split("\n") if line.strip()]

    # --------------------------------------------------------- collect & save

    def _collect(self):
        d = {}

        d["site"] = {
            "name": self.site_name_var.get().strip(),
            "base_url": self.site_url_var.get().strip(),
            "api_base": self.api_base_var.get().strip(),
            "username": self.username_var.get().strip(),
            "application_password": self.password_var.get(),
            "verify_ssl": self.ssl_var.get(),
            "timeout": int(self.timeout_var.get().strip() or "30"),
        }

        d["defaults"] = {
            "status": self.default_status_var.get(),
            "author": int(self.default_author_var.get().strip() or "1"),
            "categories": self._get_list(self.categories_txt),
            "tags": self._get_list(self.tags_txt),
            "excerpt": self.default_excerpt_var.get().strip(),
            "auto_create_categories": self.auto_cat_var.get(),
            "auto_create_tags": self.auto_tag_var.get(),
        }

        detection = self._get_list(self.detection_txt)
        for k in detection:
            if k not in VALID_DETECTION_KEYS:
                raise ValueError(f"未知的检测方式：{k}\n合法值：{', '.join(sorted(VALID_DETECTION_KEYS))}")

        d["upload"] = {
            "write_back": self.write_back_var.get(),
            "backup_before_write": self.backup_var.get(),
            "standardize_frontmatter": self.standardize_var.get(),
            "title_match_enabled": self.title_match_var.get(),
            "title_match_strict": self.title_strict_var.get(),
            "allow_publish_status": self.allow_publish_var.get(),
            "update_detection_order": detection,
        }

        d["markdown"] = {
            "convert_to_html": self.md_convert_var.get(),
            "first_h1_as_title": self.md_h1_title_var.get(),
            "remove_first_h1_from_content": self.md_remove_h1_var.get(),
            "extensions": self._get_list(self.extensions_txt),
        }

        d["notification"] = {
            "enabled": self.notify_enabled_var.get(),
            "success_popup": self.notify_success_var.get(),
            "error_popup": self.notify_error_var.get(),
        }

        d["logs"] = {
            "history_file": self.history_file_var.get().strip(),
            "latest_file": self.latest_file_var.get().strip(),
        }

        d["state"] = {
            "file": self.state_file_var.get().strip(),
        }

        return d

    def _save(self):
        try:
            new_data = self._collect()
        except ValueError as e:
            messagebox.showerror("保存失败", str(e))
            return

        try:
            self._data = new_data
            self._save_data()
            self._modified = False
            messagebox.showinfo("保存成功", f"配置已保存到 {self._config_path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"写入配置文件失败：\n{e}")

    def _reload(self):
        if self._modified:
            if not messagebox.askyesno("确认", "放弃当前未保存的修改？"):
                return
        self._load_data()
        self._populate_ui()
        messagebox.showinfo("已重新加载", "配置已从文件重新加载。")

    # ----------------------------------------------------------- test connection

    def _test_connection(self):
        try:
            cfg = Config.__new__(Config)
            cfg._data = self._collect()
        except Exception as e:
            messagebox.showerror("错误", f"配置有误：\n{e}")
            return

        self._site_result.configure(state="normal")
        self._site_result.delete("1.0", "end")
        self._site_result.insert("end", "正在测试连接…\n")
        self._site_result.configure(state="disabled")
        self.root.update()

        def work():
            try:
                client = WordPressClient(
                    base_url=cfg.base_url,
                    api_base=cfg.api_base,
                    username=cfg.username,
                    app_password=cfg.application_password,
                    verify_ssl=cfg.verify_ssl,
                    timeout=cfg.timeout,
                )
                result = client.check_auth()
                lines = []
                if result is None:
                    lines.append("[错误] 无响应")
                elif "error_code" in result:
                    lines.append(f"[错误] {result.get('http_status')} {result.get('error_code')}")
                    lines.append(f"       {result.get('error_message')}")
                else:
                    lines.append("[成功] 认证通过")
                    lines.append(f"  User ID:   {result.get('id')}")
                    lines.append(f"  Username:  {result.get('slug', result.get('name'))}")
                    lines.append(f"  Display:   {result.get('name')}")
                    lines.append(f"  Site URL:  {cfg.base_url}")
                self.root.after(0, lambda: self._show_test_result("\n".join(lines)))
            except Exception as e:
                self.root.after(0, lambda: self._show_test_result(f"[错误] {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _show_test_result(self, text):
        self._site_result.configure(state="normal")
        self._site_result.delete("1.0", "end")
        self._site_result.insert("end", text + "\n")
        self._site_result.configure(state="disabled")

    # ----------------------------------------------------------- dry-run

    def _run_dry_run(self):
        fp = filedialog.askopenfilename(
            title="选择 Markdown 文件",
            filetypes=[("Markdown", "*.md"), ("所有文件", "*.*")],
        )
        if not fp:
            return

        try:
            cfg = Config.__new__(Config)
            cfg._data = self._collect()
        except Exception as e:
            messagebox.showerror("错误", f"配置有误：\n{e}")
            return

        self._dry_run_result.configure(state="normal")
        self._dry_run_result.delete("1.0", "end")
        self._dry_run_result.insert("end", f"正在分析：{fp}\n")
        self._dry_run_result.configure(state="disabled")
        self.root.update()

        def work():
            try:
                uploader = Uploader(cfg)
                old_stdout = sys.stdout
                from io import StringIO
                buf = StringIO()
                sys.stdout = buf
                rc = uploader.upload(fp, dry_run=True)
                sys.stdout = old_stdout
                output = buf.getvalue()
                self.root.after(0, lambda: self._show_dry_run_result(output if rc == 0 else f"[失败]\n{output}"))
            except Exception as e:
                sys.stdout = old_stdout if 'old_stdout' in dir() else sys.__stdout__
                self.root.after(0, lambda: self._show_dry_run_result(f"[错误] {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _show_dry_run_result(self, text):
        self._dry_run_result.configure(state="normal")
        self._dry_run_result.delete("1.0", "end")
        self._dry_run_result.insert("end", text)
        self._dry_run_result.configure(state="disabled")

    # --------------------------------------------------------------- run

    def run(self):
        self.root.mainloop()


def main():
    app = AutoSiteConfigApp()
    app.run()


if __name__ == "__main__":
    main()
