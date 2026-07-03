import os
import sys
import json
import shutil
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from io import StringIO
from datetime import datetime

import yaml

from .config import Config, DEFAULT_CONFIG_PATH, EXAMPLE_CONFIG_PATH
from .wordpress_client import WordPressClient
from .uploader import Uploader
from .context_menu import install as ctx_install, uninstall as ctx_uninstall, is_installed as ctx_is_installed
from .gui_theme import set_dpi_aware, center_window, apply_style, make_card


VALID_DETECTION_KEYS = {"wp_post_id", "slug", "state", "title_exact_match"}
STATUS_OPTIONS = ["draft", "publish", "private", "pending", "future"]


class AutoSiteConfigApp:
    def __init__(self):
        set_dpi_aware()

        self.root = tk.Tk()
        self.root.title("AutoSite 配置工具")
        center_window(self.root, 960, 680)
        self._style = apply_style()

        self._config_path = DEFAULT_CONFIG_PATH
        self._data = {}
        self._modified = False
        self._password_visible = False

        self._ensure_config()
        self._load_data()

        self._build_ui()
        self._populate_ui()
        self._refresh_overview()
        self._refresh_ctx_status()
        self._refresh_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Control-s>", lambda e: self._save())
        self.root.bind("<Control-S>", lambda e: self._save())

    # ================================================================== init helpers

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

    # ================================================================== modified tracking

    def _mark_modified(self, *_args):
        if not self._modified:
            self._modified = True
            self.root.title("AutoSite 配置工具 *")
            self._status_var.set("有未保存修改")

    def _bind_modified(self, widget):
        if isinstance(widget, (ttk.Entry, ttk.Combobox)):
            widget.bind("<KeyRelease>", self._mark_modified)
        elif isinstance(widget, tk.Text):
            widget.bind("<KeyRelease>", self._mark_modified)

    def _bind_check_modified(self, var):
        var.trace_add("write", self._mark_modified)

    # ================================================================== build UI

    def _build_ui(self):
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=6, pady=(6, 0))

        self._tab_overview = ttk.Frame(self._notebook)
        self._tab_site = ttk.Frame(self._notebook)
        self._tab_defaults = ttk.Frame(self._notebook)
        self._tab_upload = ttk.Frame(self._notebook)
        self._tab_markdown = ttk.Frame(self._notebook)
        self._tab_notification = ttk.Frame(self._notebook)
        self._tab_context_menu = ttk.Frame(self._notebook)
        self._tab_tools = ttk.Frame(self._notebook)

        self._notebook.add(self._tab_overview, text="概览")
        self._notebook.add(self._tab_site, text="站点配置")
        self._notebook.add(self._tab_defaults, text="默认文章配置")
        self._notebook.add(self._tab_upload, text="上传行为")
        self._notebook.add(self._tab_markdown, text="Markdown 设置")
        self._notebook.add(self._tab_notification, text="通知与日志")
        self._notebook.add(self._tab_context_menu, text="右键菜单")
        self._notebook.add(self._tab_tools, text="工具")

        self._build_overview_tab()
        self._build_site_tab()
        self._build_defaults_tab()
        self._build_upload_tab()
        self._build_markdown_tab()
        self._build_notification_tab()
        self._build_context_menu_tab()
        self._build_tools_tab()
        self._build_bottom_bar()
        self._bind_modified_tracking()

    # --------------------------------------------------------------- helpers

    def _entry(self, parent, label, row=0, column=1, width=50, show=None, span=2):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
        var = tk.StringVar()
        kw = {"textvariable": var, "width": width}
        if show:
            kw["show"] = show
        w = ttk.Entry(parent, **kw)
        w.grid(row=row, column=column, columnspan=span, sticky="ew", pady=3)
        return var, w

    def _check(self, parent, label, row=0, column=1, span=2):
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(parent, text=label, variable=var)
        cb.grid(row=row, column=column, columnspan=span, sticky="w", pady=3, padx=(0, 6))
        return var, cb

    def _combo(self, parent, label, row, values, width=30, span=2):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=3)
        var = tk.StringVar()
        w = ttk.Combobox(parent, textvariable=var, values=values, width=width, state="readonly")
        w.grid(row=row, column=1, columnspan=span, sticky="w", pady=3)
        return var, w

    def _textbox(self, parent, height=5, width=55):
        f = ttk.Frame(parent)
        txt = tk.Text(f, height=height, width=width, wrap="none", font=("Consolas", 9))
        txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)
        f.pack(fill="both", expand=True)
        return txt

    def _fill_row(self, parent, widgets, row=0, pady=3):
        for i, w in enumerate(widgets):
            w.grid(row=row, column=i, sticky="w", padx=2, pady=pady)

    # ================================================================== overview tab

    def _build_overview_tab(self):
        f = self._tab_overview
        f.columnconfigure(1, weight=1)
        f.rowconfigure(3, weight=1)

        # site card
        card1 = make_card(f, "站点信息", 0, 0, colspan=2, weight=1)
        self._ov_site_name = ttk.Label(card1, text="")
        self._ov_site_name.grid(row=0, column=0, sticky="w", pady=2)
        self._ov_site_url = ttk.Label(card1, text="")
        self._ov_site_url.grid(row=1, column=0, sticky="w", pady=2)
        self._ov_api_url = ttk.Label(card1, text="")
        self._ov_api_url.grid(row=2, column=0, sticky="w", pady=2)
        self._ov_config = ttk.Label(card1, text="")
        self._ov_config.grid(row=3, column=0, sticky="w", pady=2)

        # status card
        card2 = make_card(f, "运行状态", 1, 0, colspan=2, weight=1)
        self._ov_ctx_status = ttk.Label(card2, text="")
        self._ov_ctx_status.grid(row=0, column=0, sticky="w", pady=2)
        self._ov_last_upload = ttk.Label(card2, text="")
        self._ov_last_upload.grid(row=1, column=0, sticky="w", pady=2)
        self._ov_config_status = ttk.Label(card2, text="", foreground="green")
        self._ov_config_status.grid(row=2, column=0, sticky="w", pady=2)

        # action buttons card
        card3 = make_card(f, "快捷操作", 2, 0, colspan=2, weight=1)
        ttk.Button(card3, text="保存配置", command=self._save, width=18).grid(row=0, column=0, padx=4, pady=3)
        ttk.Button(card3, text="测试连接", command=self._test_connection, width=18).grid(row=0, column=1, padx=4, pady=3)
        ttk.Button(card3, text="安装右键菜单", command=self._install_ctx_gui, width=18).grid(row=0, column=2, padx=4, pady=3)
        ttk.Button(card3, text="卸载右键菜单", command=self._uninstall_ctx_gui, width=18).grid(row=1, column=0, padx=4, pady=3)
        ttk.Button(card3, text="打开 config.yaml", command=self._open_config, width=18).grid(row=1, column=1, padx=4, pady=3)
        ttk.Button(card3, text="打开 logs 目录", command=lambda: self._open_dir("logs"), width=18).grid(row=1, column=2, padx=4, pady=3)

    def _refresh_overview(self):
        d = self._data
        site = d.get("site", {})
        self._ov_site_name.configure(text=f"站点：{site.get('name', '未设置')}")
        self._ov_site_url.configure(text=f"地址：{site.get('base_url', '未设置')}")
        self._ov_api_url.configure(text=f"API：{site.get('api_base', '未设置')}")
        self._ov_config.configure(text=f"配置文件：{os.path.abspath(self._config_path)}")
        ctx = "已安装" if ctx_is_installed() else "未安装"
        self._ov_ctx_status.configure(text=f"右键菜单：{ctx}")
        latest_path = d.get("logs", {}).get("latest_file", "logs/upload-latest.json")
        latest_absp = os.path.abspath(latest_path)
        if os.path.isfile(latest_absp):
            try:
                with open(latest_absp, "r", encoding="utf-8") as lf:
                    last = json.load(lf)
                if last.get("success"):
                    self._ov_last_upload.configure(text=f"最近上传：成功 ({last.get('action', '?')})", foreground="green")
                else:
                    self._ov_last_upload.configure(text=f"最近上传：失败 ({last.get('error_code', '?')})", foreground="red")
            except Exception:
                self._ov_last_upload.configure(text="最近上传：读取失败", foreground="gray")
        else:
            self._ov_last_upload.configure(text="最近上传：无记录", foreground="gray")
        self._ov_config_status.configure(text="config.yaml 已就绪")

    # ================================================================== site tab

    def _build_site_tab(self):
        f = self._tab_site
        f.columnconfigure(1, weight=1)

        card1 = make_card(f, "站点信息", 0, 0, colspan=3, weight=1)
        self.site_name_var, self.site_name_entry = self._entry(card1, "站点名称", 0)
        self.site_url_var, self.site_url_entry = self._entry(card1, "站点地址", 1)
        self.api_base_var, self.api_base_entry = self._entry(card1, "API 地址", 2)

        card2 = make_card(f, "认证信息", 1, 0, colspan=3, weight=1)
        self.username_var, self.username_entry = self._entry(card2, "用户名", 0)
        self.password_var, self.password_entry = self._entry(card2, "应用程序密码", 1, show="*")

        pw_frame = ttk.Frame(card2)
        pw_frame.grid(row=1, column=3, sticky="w", padx=(4, 0), pady=3)
        self._btn_toggle_pw = ttk.Button(pw_frame, text="显示", command=self._toggle_password, width=8)
        self._btn_toggle_pw.pack(side="left", padx=1)
        ttk.Label(card2, text="密码只保存在 config.yaml，不会写入日志",
                  foreground="gray", wraplength=280, font=("", 8)).grid(row=2, column=1, columnspan=3, sticky="w", padx=(0, 4))

        card3 = make_card(f, "连接设置", 2, 0, colspan=3, weight=1)
        self.ssl_var, _ = self._check(card3, "验证 SSL", 0)
        ttk.Label(card3, text="请求超时（秒）").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.timeout_var = tk.StringVar()
        self.timeout_entry = ttk.Entry(card3, textvariable=self.timeout_var, width=10)
        self.timeout_entry.grid(row=1, column=1, sticky="w", pady=3)
        ttk.Button(card3, text="测试连接", command=self._test_connection).grid(row=2, column=0, columnspan=4, pady=6)

        # site result (fills remaining space)
        self._site_result = tk.Text(f, height=5, state="disabled", wrap="word", font=("Consolas", 9))
        self._site_result.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=4, padx=8)
        f.rowconfigure(3, weight=1)

    def _toggle_password(self):
        self._password_visible = not self._password_visible
        self.password_entry.configure(show="" if self._password_visible else "*")
        self._btn_toggle_pw.configure(text="隐藏" if self._password_visible else "显示")

    # ================================================================== defaults tab

    def _build_defaults_tab(self):
        f = self._tab_defaults
        f.columnconfigure(1, weight=1)
        f.rowconfigure(3, weight=1)

        card1 = make_card(f, "默认发布属性", 0, 0, colspan=3, weight=1)
        self.default_status_var, self.default_status_combo = self._combo(card1, "默认状态", 0, STATUS_OPTIONS)
        self.default_author_var, self.default_author_entry = self._entry(card1, "默认作者 ID", 1, width=10)
        self.default_excerpt_var, self.default_excerpt_entry = self._entry(card1, "默认摘要", 2, width=50)
        self._status_warn = ttk.Label(card1, text="", foreground="red", wraplength=500)
        self._status_warn.grid(row=3, column=0, columnspan=4, sticky="w", pady=2, padx=(10, 0))

        card2 = make_card(f, "默认分类与标签", 1, 0, colspan=3, weight=1)
        ttk.Label(card2, text="每行一个分类/标签名称").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2, columnspan=2)
        ttk.Label(card2, text="分类").grid(row=0, column=0, sticky="w", pady=2)
        f1 = ttk.Frame(card2)
        f1.grid(row=1, column=0, sticky="nsew", padx=2)
        f1.columnconfigure(0, weight=1)
        self.categories_txt = self._textbox(f1, height=4)

        ttk.Label(card2, text="标签").grid(row=0, column=1, sticky="w", pady=2)
        f2 = ttk.Frame(card2)
        f2.grid(row=1, column=1, sticky="nsew", padx=2)
        f2.columnconfigure(0, weight=1)
        self.tags_txt = self._textbox(f2, height=4)

        card3 = make_card(f, "自动创建", 2, 0, colspan=3, weight=1)
        self.auto_cat_var, _ = self._check(card3, "自动创建分类 auto_create_categories", 0)
        self.auto_tag_var, _ = self._check(card3, "自动创建标签 auto_create_tags", 1)

        self.default_status_var.trace_add("write", lambda *a: self._check_status_warning())

    def _check_status_warning(self):
        status = self.default_status_var.get()
        allow = self.allow_publish_var.get() if hasattr(self, "allow_publish_var") else False
        if status == "publish" and not allow:
            self._status_warn.configure(text="当前配置不允许直接发布，实际上传时会降级为 draft")
        else:
            self._status_warn.configure(text="")

    # ================================================================== upload tab

    def _build_upload_tab(self):
        f = self._tab_upload
        f.columnconfigure(1, weight=1)
        f.rowconfigure(2, weight=1)

        card1 = make_card(f, "上传后行为", 0, 0, colspan=3, weight=1)
        self.write_back_var, _ = self._check(card1, "上传后写回 Markdown", 0)
        self.backup_var, _ = self._check(card1, "写回前备份原文件", 1)
        self.standardize_var, _ = self._check(card1, "标准化 Front Matter", 2)

        card2 = make_card(f, "标题匹配", 1, 0, colspan=3, weight=1)
        self.title_match_var, _ = self._check(card2, "允许标题匹配查找已有文章", 0)
        self.title_strict_var, _ = self._check(card2, "标题必须严格相等", 1)
        self.allow_publish_var, _ = self._check(card2, "允许直接发布 publish", 2)
        self._publish_warn = ttk.Label(card2, text="开启后 Markdown 中 status: publish 会直接发布到网站",
                                       foreground="red", wraplength=500)
        self._publish_warn.grid(row=3, column=0, columnspan=4, sticky="w", padx=(20, 0), pady=(0, 2))
        self.allow_publish_var.trace_add("write", lambda *a: self._check_publish_warning())

        card3 = make_card(f, "更新检测顺序", 2, 0, colspan=3, weight=1)
        self.detection_txt = self._textbox(card3, height=5)
        ttk.Label(card3, text="每行一个检测方式，合法值：wp_post_id, slug, state, title_exact_match",
                  foreground="gray").pack(anchor="w", pady=(2, 0))

    def _check_publish_warning(self):
        if self.allow_publish_var.get():
            self._publish_warn.configure(text="")
        else:
            self._publish_warn.configure(text="开启后 Markdown 中 status: publish 会直接发布到网站")

    # ================================================================== markdown tab

    def _build_markdown_tab(self):
        f = self._tab_markdown
        f.columnconfigure(1, weight=1)
        f.rowconfigure(2, weight=1)

        card1 = make_card(f, "HTML 转换", 0, 0, colspan=3, weight=1)
        self.md_convert_var, _ = self._check(card1, "Markdown 转 HTML 后提交", 0)
        self.md_h1_title_var, _ = self._check(card1, "取第一个 H1 作为文章标题", 1)
        self.md_remove_h1_var, _ = self._check(card1, "从正文中移除第一个 H1", 2)

        card2 = make_card(f, "Markdown 扩展", 1, 0, colspan=3, weight=1)
        ttk.Label(card2, text="每行一个扩展名").pack(anchor="w", pady=(0, 2))
        self.extensions_txt = self._textbox(card2, height=6)
        ttk.Label(card2, text="常用：extra, tables, fenced_code, codehilite, toc, sane_lists",
                  foreground="gray").pack(anchor="w", pady=(2, 0))

    # ================================================================== notification tab

    def _build_notification_tab(self):
        f = self._tab_notification
        f.columnconfigure(1, weight=1)
        f.rowconfigure(4, weight=1)

        card1 = make_card(f, "弹窗通知", 0, 0, colspan=3, weight=1)
        self.notify_enabled_var, _ = self._check(card1, "启用通知", 0)
        self.notify_success_var, _ = self._check(card1, "上传成功时弹窗", 1)
        self.notify_error_var, _ = self._check(card1, "上传失败时弹窗", 2)

        card2 = make_card(f, "日志文件路径", 1, 0, colspan=3, weight=1)
        self.history_file_var, self.history_entry = self._entry(card2, "历史日志", 0, width=40)
        ttk.Button(card2, text="打开", command=lambda: self._open_file_var(self.history_file_var), width=8).grid(row=0, column=3, padx=2)

        self.latest_file_var, self.latest_entry = self._entry(card2, "最新结果", 1, width=40)
        ttk.Button(card2, text="打开", command=lambda: self._open_file_var(self.latest_file_var), width=8).grid(row=1, column=3, padx=2)

        self.state_file_var, self.state_entry = self._entry(card2, "状态文件", 2, width=40)
        ttk.Button(card2, text="打开", command=lambda: self._open_file_var(self.state_file_var), width=8).grid(row=2, column=3, padx=2)

        card3 = make_card(f, "快速打开目录", 2, 0, colspan=3, weight=1)
        ttk.Button(card3, text="打开 logs 目录", command=lambda: self._open_dir("logs"), width=16).pack(side="left", padx=4, pady=2)
        ttk.Button(card3, text="打开 state 目录", command=lambda: self._open_dir("state"), width=16).pack(side="left", padx=4, pady=2)

        self._bind_entry_modified(self.history_entry)
        self._bind_entry_modified(self.latest_entry)
        self._bind_entry_modified(self.state_entry)

    def _open_file_var(self, var):
        p = var.get().strip()
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

    # ================================================================== context menu tab

    def _build_context_menu_tab(self):
        f = self._tab_context_menu
        f.columnconfigure(0, weight=1)

        card = make_card(f, "右键菜单状态", 0, 0, colspan=1, weight=1)
        self._ctx_status_label = ttk.Label(card, text="检查中…", font=("Microsoft YaHei UI", 12, "bold"))
        self._ctx_status_label.grid(row=0, column=0, sticky="w", pady=4)

        info_text = ("菜单名称：上传到 threcial.cn\n"
                     "作用范围：.md 文件\n"
                     "注册位置：HKCU 当前用户（无需管理员权限）")
        ttk.Label(card, text=info_text, justify="left", foreground="gray").grid(row=1, column=0, sticky="w", pady=4)

        self._ctx_install_btn = ttk.Button(card, text="安装右键菜单", command=self._install_ctx_gui, width=20)
        self._ctx_install_btn.grid(row=2, column=0, sticky="w", pady=4, padx=2)

        self._ctx_uninstall_btn = ttk.Button(card, text="卸载右键菜单", command=self._uninstall_ctx_gui, width=20)
        self._ctx_uninstall_btn.grid(row=3, column=0, sticky="w", pady=4, padx=2)

        ttk.Button(card, text="刷新状态", command=self._refresh_ctx_status, width=20).grid(row=4, column=0, sticky="w", pady=4, padx=2)

    def _refresh_ctx_status(self):
        installed = ctx_is_installed()
        if installed:
            self._ctx_status_label.configure(text="✓ 已安装", foreground="green")
            self._ctx_install_btn.configure(text="重新安装")
            self._ctx_uninstall_btn.configure(state="normal")
        else:
            self._ctx_status_label.configure(text="✗ 未安装", foreground="red")
            self._ctx_install_btn.configure(text="安装右键菜单")
            self._ctx_uninstall_btn.configure(state="disabled")
        self._ov_ctx_status.configure(text=f"右键菜单：{'已安装' if installed else '未安装'}")
        self._refresh_status_bar()

    def _install_ctx_gui(self):
        self._status_var.set("正在安装右键菜单...")
        self.root.update()
        ok, msg = ctx_install()
        if ok:
            messagebox.showinfo("成功", "右键菜单已安装。请重新打开资源管理器窗口后测试。")
            self._status_var.set("右键菜单已安装")
        else:
            messagebox.showerror("失败", msg)
            self._status_var.set(f"安装失败：{msg}")
        self._refresh_ctx_status()

    def _uninstall_ctx_gui(self):
        self._status_var.set("正在卸载右键菜单...")
        self.root.update()
        ok, msg = ctx_uninstall()
        if ok:
            messagebox.showinfo("成功", "右键菜单已卸载。")
            self._status_var.set("右键菜单已卸载")
        else:
            messagebox.showerror("失败", msg)
            self._status_var.set(f"卸载失败：{msg}")
        self._refresh_ctx_status()

    # ================================================================== tools tab

    def _build_tools_tab(self):
        f = self._tab_tools
        f.columnconfigure(1, weight=1)
        f.rowconfigure(2, weight=1)

        card1 = make_card(f, "快速操作", 0, 0, colspan=2, weight=1)
        ttk.Button(card1, text="测试 WordPress 连接", command=self._test_connection, width=30).grid(row=0, column=0, padx=4, pady=3)
        ttk.Button(card1, text="选择 Markdown 文件 dry-run", command=self._run_dry_run, width=30).grid(row=0, column=1, padx=4, pady=3)
        ttk.Button(card1, text="打开 config.yaml", command=self._open_config, width=30).grid(row=1, column=0, padx=4, pady=3)
        ttk.Button(card1, text="打开项目目录", command=self._open_project_dir, width=30).grid(row=1, column=1, padx=4, pady=3)
        ttk.Button(card1, text="打开 README", command=self._open_readme, width=30).grid(row=2, column=0, padx=4, pady=3)
        ttk.Button(card1, text="打开 logs 目录", command=lambda: self._open_dir("logs"), width=30).grid(row=2, column=1, padx=4, pady=3)

        card2 = make_card(f, "Dry-Run 结果", 1, 0, colspan=2, weight=1)
        self._dry_run_result = tk.Text(card2, height=10, state="disabled", wrap="word", font=("Consolas", 9))
        self._dry_run_result.pack(fill="both", expand=True, padx=2, pady=2)

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

    # ================================================================== bottom bar & status

    def _build_bottom_bar(self):
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=(4, 6))

        ttk.Button(bar, text="保存配置", command=self._save, width=14).pack(side="left", padx=2)
        ttk.Button(bar, text="重新加载", command=self._reload, width=14).pack(side="left", padx=2)
        ttk.Button(bar, text="测试连接", command=self._test_connection, width=14).pack(side="left", padx=2)
        ttk.Button(bar, text="退出", command=self._on_close, width=10).pack(side="right", padx=2)

        self._status_var = tk.StringVar()
        self._status_var.set("就绪")
        self._status_bar = ttk.Label(
            self.root, textvariable=self._status_var, relief="sunken",
            anchor="w", padding=(6, 3),
        )
        self._status_bar.pack(fill="x", padx=0, pady=0, side="bottom")

    def _refresh_status_bar(self):
        ctx = "已安装" if ctx_is_installed() else "未安装"
        self._status_var.set(f"就绪 | {self._config_path} | 右键菜单：{ctx}")

    # ================================================================== populate

    def _populate_ui(self):
        d = self._data

        site = d.get("site", {})
        self._set(self.site_name_var, site.get("name", ""))
        self._set(self.site_url_var, site.get("base_url", ""))
        self._set(self.api_base_var, site.get("api_base", ""))
        self._set(self.username_var, site.get("username", ""))
        self._set(self.password_var, site.get("application_password", ""))
        self._set(self.ssl_var, site.get("verify_ssl", True))
        self._set(self.timeout_var, str(site.get("timeout", 30)))

        defaults = d.get("defaults", {})
        self._set(self.default_status_var, defaults.get("status", "draft"))
        self._set(self.default_author_var, str(defaults.get("author", 1)))
        self._set(self.default_excerpt_var, defaults.get("excerpt", ""))
        self._set_list(self.categories_txt, defaults.get("categories", []))
        self._set_list(self.tags_txt, defaults.get("tags", []))
        self._set(self.auto_cat_var, defaults.get("auto_create_categories", False))
        self._set(self.auto_tag_var, defaults.get("auto_create_tags", True))

        upload = d.get("upload", {})
        self._set(self.write_back_var, upload.get("write_back", True))
        self._set(self.backup_var, upload.get("backup_before_write", True))
        self._set(self.standardize_var, upload.get("standardize_frontmatter", True))
        self._set(self.title_match_var, upload.get("title_match_enabled", True))
        self._set(self.title_strict_var, upload.get("title_match_strict", True))
        self._set(self.allow_publish_var, upload.get("allow_publish_status", False))
        self._set_list(self.detection_txt, upload.get("update_detection_order",
                                                       ["wp_post_id", "slug", "state", "title_exact_match"]))

        md = d.get("markdown", {})
        self._set(self.md_convert_var, md.get("convert_to_html", True))
        self._set(self.md_h1_title_var, md.get("first_h1_as_title", True))
        self._set(self.md_remove_h1_var, md.get("remove_first_h1_from_content", False))
        self._set_list(self.extensions_txt, md.get("extensions",
                                                     ["extra", "tables", "fenced_code", "codehilite", "toc", "sane_lists"]))

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
        self.root.title("AutoSite 配置工具")

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

    @staticmethod
    def _get_list(txt):
        raw = txt.get("1.0", "end").strip()
        if not raw:
            return []
        return [line.strip() for line in raw.split("\n") if line.strip()]

    def _bind_entry_modified(self, entry):
        entry.bind("<KeyRelease>", self._mark_modified)

    def _bind_modified_tracking(self):
        entries = [
            self.site_name_entry, self.site_url_entry, self.api_base_entry,
            self.username_entry, self.password_entry, self.timeout_entry,
            self.default_author_entry, self.default_excerpt_entry,
            self.history_entry, self.latest_entry, self.state_entry,
        ]
        for e in entries:
            e.bind("<KeyRelease>", self._mark_modified)

        texts = [
            self.categories_txt, self.tags_txt,
            self.detection_txt, self.extensions_txt,
        ]
        for t in texts:
            t.bind("<KeyRelease>", self._mark_modified)

        bool_vars = [
            self.ssl_var, self.auto_cat_var, self.auto_tag_var,
            self.write_back_var, self.backup_var, self.standardize_var,
            self.title_match_var, self.title_strict_var, self.allow_publish_var,
            self.md_convert_var, self.md_h1_title_var, self.md_remove_h1_var,
            self.notify_enabled_var, self.notify_success_var, self.notify_error_var,
        ]
        for v in bool_vars:
            v.trace_add("write", self._mark_modified)

        self.default_status_var.trace_add("write", self._mark_modified)

    # ================================================================== collect & save

    def _collect(self):
        d = dict(self._data)
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
            self.root.title("AutoSite 配置工具")
            self._refresh_overview()
            self._status_var.set(f"配置已保存到 {self._config_path}")
            messagebox.showinfo("保存成功", f"配置已保存到 {self._config_path}")
        except Exception as e:
            self._status_var.set(f"保存失败：{e}")
            messagebox.showerror("保存失败", f"写入配置文件失败：\n{e}")

    def _reload(self):
        if self._modified:
            if not messagebox.askyesno("确认", "放弃当前未保存的修改？"):
                return
        self._load_data()
        self._populate_ui()
        self._refresh_overview()
        self._refresh_ctx_status()
        self._status_var.set("配置已重新加载")
        messagebox.showinfo("已重新加载", "配置已从文件重新加载。")

    # ================================================================== test connection

    def _test_connection(self):
        try:
            cfg = Config.__new__(Config)
            cfg._data = self._collect()
        except Exception as e:
            self._status_var.set(f"配置有误：{e}")
            messagebox.showerror("错误", f"配置有误：\n{e}")
            return

        self._status_var.set("正在测试连接...")
        self._site_result.configure(state="normal")
        self._site_result.delete("1.0", "end")
        self._site_result.insert("end", "正在测试连接…\n")
        self._site_result.configure(state="disabled")
        self.root.update()

        def work():
            try:
                client = WordPressClient(
                    base_url=cfg.base_url, api_base=cfg.api_base,
                    username=cfg.username, app_password=cfg.application_password,
                    verify_ssl=cfg.verify_ssl, timeout=cfg.timeout,
                )
                result = client.check_auth()
                lines = []
                if result is None:
                    lines.append("✗ 无响应")
                    self.root.after(0, lambda: self._status_var.set("测试连接失败：无响应"))
                elif "error_code" in result:
                    lines.append(f"✗ {result.get('http_status')} {result.get('error_code')}")
                    lines.append(f"  {result.get('error_message')}")
                    self.root.after(0, lambda: self._status_var.set(f"测试连接失败：{result.get('error_code')}"))
                else:
                    lines.append("✓ 认证通过")
                    lines.append(f"  User ID:   {result.get('id')}")
                    lines.append(f"  Username:  {result.get('slug', result.get('name'))}")
                    lines.append(f"  Display:   {result.get('name')}")
                    lines.append(f"  Site URL:  {cfg.base_url}")
                    self.root.after(0, lambda: self._status_var.set("测试连接成功"))
                self.root.after(0, lambda: self._show_test_result("\n".join(lines)))
            except Exception as e:
                self.root.after(0, lambda: self._status_var.set(f"测试连接异常：{e}"))
                self.root.after(0, lambda: self._show_test_result(f"[错误] {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _show_test_result(self, text):
        self._site_result.configure(state="normal")
        self._site_result.delete("1.0", "end")
        self._site_result.insert("end", text + "\n")
        self._site_result.configure(state="disabled")

    # ================================================================== dry-run

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
            self._status_var.set(f"配置有误：{e}")
            messagebox.showerror("错误", f"配置有误：\n{e}")
            return

        self._status_var.set("正在执行 dry-run...")
        self._dry_run_result.configure(state="normal")
        self._dry_run_result.delete("1.0", "end")
        self._dry_run_result.configure(state="disabled")
        self.root.update()

        def work():
            try:
                uploader = Uploader(cfg)
                old_stdout = sys.stdout
                buf = StringIO()
                sys.stdout = buf
                rc = uploader.upload(fp, dry_run=True)
                sys.stdout = old_stdout
                output = buf.getvalue()
                self.root.after(0, lambda: self._show_dry_run_result(output if rc == 0 else f"[失败]\n{output}"))
                self.root.after(0, lambda: self._status_var.set("Dry-run 完成" if rc == 0 else "Dry-run 失败"))
            except Exception as e:
                sys.stdout = sys.__stdout__
                self.root.after(0, lambda: self._show_dry_run_result(f"[错误] {e}"))
                self.root.after(0, lambda: self._status_var.set(f"Dry-run 错误：{e}"))

        threading.Thread(target=work, daemon=True).start()

    def _show_dry_run_result(self, text):
        self._dry_run_result.configure(state="normal")
        self._dry_run_result.delete("1.0", "end")
        self._dry_run_result.insert("end", text)
        self._dry_run_result.configure(state="disabled")

    # ================================================================== run

    def run(self):
        self.root.mainloop()


def main():
    app = AutoSiteConfigApp()
    app.run()


if __name__ == "__main__":
    main()
