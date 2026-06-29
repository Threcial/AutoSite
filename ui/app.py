import sys
import os
import io
import json
import contextlib
import glob

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.wordpress_client import WordPressClient
from src.article_parser import parse_markdown_file, parse_article_lenient, markdown_to_html
from src.publisher import Publisher
from src.file_manager import ensure_article_dirs, is_raw_article, is_published_article

# ---------------------------------------------------------------------------
ensure_article_dirs()

HIDE_STREAMLIT = """
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
"""
LAYOUT_CSS = """
    .block-container { max-width: 1280px; padding-top: 1rem; padding-bottom: 1rem; }
    .card { background: var(--secondary-background-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 0.8em; font-weight: 600; }
    .badge-ok { background: #1a8a1a; color: #fff; }
    .badge-err { background: #b91c1c; color: #fff; }
"""
CUSTOM_CSS = HIDE_STREAMLIT + LAYOUT_CSS

# ---------------------------------------------------------------------------

def load_config():
    return Config()


def make_client(config):
    return WordPressClient(
        base_url=config.base_url,
        username=config.username,
        app_password=config.app_password,
        verify_ssl=config.verify_ssl,
    )


def list_md_files(directory):
    return sorted(glob.glob(os.path.join(directory, "*.md")))


def raw_files():
    return list_md_files("articles/raw")


def published_files():
    return list_md_files("articles/published")


def site_badge_html(config, user):
    if user:
        return f'<span class="badge badge-ok">● {config.base_url}</span>'
    return f'<span class="badge badge-err">○ Disconnected</span>'


# =============================== PAGES ===================================

def page_create(config):
    files = raw_files()
    if not files:
        st.info("articles/raw/ 下没有 Markdown 文件")
        return

    selected = st.selectbox("选择新文章", files, format_func=os.path.basename, key="c_file")
    if not selected:
        return

    article, defaults = parse_article_lenient(selected, config)
    if article is None:
        st.error("文章解析失败")
        return

    if defaults:
        st.info("该文件没有完整 Front Matter，发布时将自动补全")

    tab_md, tab_html, tab_json, tab_log = st.tabs(["Markdown 原文", "HTML 预览", "WordPress JSON", "日志"])
    with tab_md:
        with open(selected, "r", encoding="utf-8") as f:
            st.text_area("", f.read(), height=400, label_visibility="collapsed")
    with tab_html:
        st.markdown(article.content_html, unsafe_allow_html=True)
        with st.expander("源码"):
            st.code(article.content_html, language="html")
    with tab_json:
        st.info("运行 Dry Run 后在此显示最终 JSON")
    with tab_log:
        st.info("运行操作后在此显示日志")

    st.divider()

    st.text_input("标题", value=article.title, key="c_title")
    st.text_input("Slug", value="发布后由 WordPress 自动生成", disabled=True)
    st.selectbox("状态", ["draft", "publish", "pending", "private"],
                 index=["draft", "publish", "pending", "private"].index(article.status) if article.status in ["draft", "publish", "pending", "private"] else 0,
                 key="c_status")

    auth_user = st.session_state.get("auth_user")
    if st.session_state.get("wp_users"):
        user_names = [f"{n} (ID {i})" for n, i in st.session_state.wp_users]
        auth_id = auth_user["id"] if auth_user else config.default_author
        default_idx = 0
        for idx, (n, i) in enumerate(st.session_state.wp_users):
            if i == (article.author or auth_id):
                default_idx = idx
                break
        sel = st.selectbox("作者", user_names, index=default_idx, key="c_author")
        edit_author = st.session_state.wp_users[user_names.index(sel)][1]
    else:
        fallback = article.author or config.default_author
        st.text_input("作者", value=f"{auth_user.get('name', '?') if auth_user else '?'} (ID {fallback})", disabled=True, key="c_author_d")
        edit_author = fallback

    with st.expander("分类与标签"):
        cat_names = [c[0] for c in st.session_state.get("wp_categories", [])]
        tag_names = [t[0] for t in st.session_state.get("wp_tags", [])]
        pre_cats = [c for c in article.categories if c in cat_names]
        edit_cats = st.multiselect("分类", cat_names, default=pre_cats, key="c_cats")
        edit_cats_custom = st.text_input("自定义分类（逗号分隔）", value=", ".join(c for c in article.categories if c not in cat_names), key="c_cats_custom")
        pre_tags = [t for t in article.tags if t in tag_names]
        edit_tags = st.multiselect("标签", tag_names, default=pre_tags, key="c_tags")
        edit_tags_custom = st.text_input("自定义标签（逗号分隔）", value=", ".join(t for t in article.tags if t not in tag_names), key="c_tags_custom")

    all_cats = list(edit_cats)
    if edit_cats_custom.strip():
        all_cats += [c.strip() for c in edit_cats_custom.split(",") if c.strip()]
    all_tags = list(edit_tags)
    if edit_tags_custom.strip():
        all_tags += [t.strip() for t in edit_tags_custom.split(",") if t.strip()]

    with st.expander("高级选项"):
        edit_excerpt = st.text_area("摘要", value=article.excerpt or "", key="c_excerpt", height=80)
        force_create = st.checkbox("--force-create：即使有 wp_post_id 也强制创建", key="c_force")
        no_wb = st.checkbox("不写回本地文件", key="c_no_wb")

    st.divider()

    confirm_publish = True
    if st.session_state.get("c_status") == "publish":
        confirm_publish = st.checkbox("⚠️ 确认直接发布为公开文章", key="c_confirm")

    dry_btn = st.button("▶ Dry Run", use_container_width=True, type="primary", key="c_dry")

    pub_ok = st.session_state.get("c_dry_ok", False) and confirm_publish
    pub_btn = st.button("创建新文章", use_container_width=True, disabled=not pub_ok,
                        help=None if pub_ok else ("请先 Dry Run" if not st.session_state.get("c_dry_ok") else "请勾选确认"),
                        type="secondary", key="c_pub")

    if dry_btn or pub_btn:
        is_dry = dry_btn
        overrides = {}
        if st.session_state.c_title != article.title:
            overrides["title"] = st.session_state.c_title
        if st.session_state.c_status != article.status:
            overrides["status"] = st.session_state.c_status
        if edit_author != article.author:
            overrides["author"] = edit_author
        if all_cats != article.categories:
            overrides["categories"] = all_cats
        if all_tags != article.tags:
            overrides["tags"] = all_tags
        if st.session_state.c_excerpt.strip() != (article.excerpt or ""):
            overrides["excerpt"] = st.session_state.c_excerpt.strip() or None

        publisher = Publisher(config)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = publisher.publish(
                selected,
                dry_run=is_dry,
                force_create=force_create,
                no_write_back=no_wb,
                overrides=overrides if overrides else None,
            )
        log_text = buf.getvalue()

        with tab_json:
            in_json = False
            jl = []
            for line in log_text.splitlines():
                if "final request JSON" in line:
                    in_json = True; continue
                if in_json:
                    if "Dry run complete" in line or "Post created" in line:
                        break
                    jl.append(line)
            if jl:
                try:
                    tab_json.json(json.loads("\n".join(jl)))
                except json.JSONDecodeError:
                    tab_json.text("\n".join(jl))
            else:
                tab_json.info("JSON 未生成")

        with tab_log:
            tab_log.text(log_text.strip())

        if is_dry:
            if result["success"]:
                st.session_state.c_dry_ok = True
                st.toast("Dry Run 成功", icon="✅")
            else:
                st.session_state.c_dry_ok = False
                st.toast("Dry Run 失败", icon="❌")
            st.rerun()
        else:
            st.session_state.c_dry_ok = False
            if result["success"]:
                parts = ["✅ 新文章发布成功"]
                parts.append(f"\n\n**文章 ID：**{result['post_id']}")
                parts.append(f"\n**Slug：**{result['slug']}")
                parts.append(f"\n**状态：**{result['status']}")
                if result["link"]:
                    parts.append(f"\n**链接：**[{result['link']}]({result['link']})")
                if result["write_back"]:
                    parts.append(f"\n\n✅ 已写回本地 Markdown")
                else:
                    parts.append(f"\n\nℹ️ 未写回本地 Markdown")
                if result.get("source_after"):
                    parts.append(f"\n\n✅ 文件已移至 `{result['source_after']}`")
                st.success("".join(parts))
            else:
                parts = ["❌ 发布失败"]
                if result["error_code"]:
                    parts.append(f"\n\n**错误代码：**`{result['error_code']}`")
                if result["error_message"]:
                    parts.append(f"\n\n**错误信息：**{result['error_message']}")
                if result["http_status"]:
                    parts.append(f"\n\n**HTTP 状态：**{result['http_status']}")
                st.error("".join(parts))


def page_update(config):
    files = published_files()
    if not files:
        st.info("articles/published/ 下没有 Markdown 文件")
        return

    selected = st.selectbox("选择已发布文章", files, format_func=os.path.basename, key="u_file")
    if not selected:
        return

    article = parse_markdown_file(selected)
    if article is None:
        st.error("文章解析失败")
        return

    wp_pid = article.raw_front_matter.get("wp_post_id")
    wp_link = article.raw_front_matter.get("wp_link", "")
    can_update = wp_pid is not None or article.slug

    if not can_update:
        st.error("该文件缺少 wp_post_id 和 slug，无法更新")
        st.info("请移动到 articles/raw/ 作为新文章发布，或手动补充 wp_post_id")
        return

    tab_md, tab_html, tab_json, tab_log = st.tabs(["Markdown 原文", "HTML 预览", "WordPress JSON", "日志"])
    with tab_md:
        with open(selected, "r", encoding="utf-8") as f:
            st.text_area("", f.read(), height=400, label_visibility="collapsed")
    with tab_html:
        st.markdown(article.content_html, unsafe_allow_html=True)
        with st.expander("源码"):
            st.code(article.content_html, language="html")
    with tab_json:
        st.info("运行 Dry Run 后在此显示最终 JSON")
    with tab_log:
        st.info("运行操作后在此显示日志")

    st.divider()

    st.markdown(f"**文章 ID：** {wp_pid or '未知'}")
    st.markdown(f"**Slug：** {article.slug or '未知'}")
    if wp_link:
        st.markdown(f"**链接：** [{wp_link}]({wp_link})")
    else:
        st.markdown("**链接：** 未知")

    st.text_input("标题", value=article.title, key="u_title")
    st.selectbox("状态", ["draft", "publish", "pending", "private"],
                 index=["draft", "publish", "pending", "private"].index(article.status) if article.status in ["draft", "publish", "pending", "private"] else 0,
                 key="u_status")

    with st.expander("分类与标签"):
        cat_names = [c[0] for c in st.session_state.get("wp_categories", [])]
        tag_names = [t[0] for t in st.session_state.get("wp_tags", [])]
        pre_cats = [c for c in article.categories if c in cat_names]
        edit_cats = st.multiselect("分类", cat_names, default=pre_cats, key="u_cats")
        edit_cats_custom = st.text_input("自定义分类", value=", ".join(c for c in article.categories if c not in cat_names), key="u_cats_custom")
        pre_tags = [t for t in article.tags if t in tag_names]
        edit_tags = st.multiselect("标签", tag_names, default=pre_tags, key="u_tags")
        edit_tags_custom = st.text_input("自定义标签", value=", ".join(t for t in article.tags if t not in tag_names), key="u_tags_custom")

    all_cats = list(edit_cats)
    if edit_cats_custom.strip():
        all_cats += [c.strip() for c in edit_cats_custom.split(",") if c.strip()]
    all_tags = list(edit_tags)
    if edit_tags_custom.strip():
        all_tags += [t.strip() for t in edit_tags_custom.split(",") if t.strip()]

    with st.expander("高级选项"):
        edit_excerpt = st.text_area("摘要", value=article.excerpt or "", key="u_excerpt", height=80)
        no_wb = st.checkbox("不写回本地文件", key="u_no_wb")

    st.divider()

    confirm_publish = True
    if st.session_state.get("u_status") == "publish":
        confirm_publish = st.checkbox("⚠️ 确认直接发布", key="u_confirm")

    dry_btn = st.button("▶ Dry Run", use_container_width=True, type="primary", key="u_dry")
    pub_ok = st.session_state.get("u_dry_ok", False) and confirm_publish
    pub_btn = st.button("更新文章", use_container_width=True, disabled=not pub_ok,
                        help=None if pub_ok else ("请先 Dry Run" if not st.session_state.get("u_dry_ok") else "请勾选确认"),
                        type="secondary", key="u_pub")

    if dry_btn or pub_btn:
        is_dry = dry_btn
        overrides = {}
        if st.session_state.u_title != article.title:
            overrides["title"] = st.session_state.u_title
        if st.session_state.u_status != article.status:
            overrides["status"] = st.session_state.u_status
        if all_cats != article.categories:
            overrides["categories"] = all_cats
        if all_tags != article.tags:
            overrides["tags"] = all_tags
        if st.session_state.u_excerpt.strip() != (article.excerpt or ""):
            overrides["excerpt"] = st.session_state.u_excerpt.strip() or None

        publisher = Publisher(config)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = publisher.publish(
                selected,
                dry_run=is_dry,
                no_write_back=no_wb,
                overrides=overrides if overrides else None,
            )
        log_text = buf.getvalue()

        with tab_json:
            in_json = False
            jl = []
            for line in log_text.splitlines():
                if "final request JSON" in line:
                    in_json = True; continue
                if in_json:
                    if "Dry run complete" in line or "Post updated" in line:
                        break
                    jl.append(line)
            if jl:
                try:
                    tab_json.json(json.loads("\n".join(jl)))
                except json.JSONDecodeError:
                    tab_json.text("\n".join(jl))
            else:
                tab_json.info("JSON 未生成")

        with tab_log:
            tab_log.text(log_text.strip())

        if is_dry:
            if result["success"]:
                st.session_state.u_dry_ok = True
                st.toast("Dry Run 成功", icon="✅")
            else:
                st.session_state.u_dry_ok = False
                st.toast("Dry Run 失败", icon="❌")
            st.rerun()
        else:
            st.session_state.u_dry_ok = False
            if result["success"]:
                parts = ["✅ 文章更新成功"]
                parts.append(f"\n\n**文章 ID：**{result['post_id']}")
                parts.append(f"\n**Slug：**{result['slug']}")
                parts.append(f"\n**状态：**{result['status']}")
                if result["link"]:
                    parts.append(f"\n**链接：**[{result['link']}]({result['link']})")
                if result["write_back"]:
                    parts.append(f"\n\n✅ 已更新本地 Front Matter")
                else:
                    parts.append(f"\n\nℹ️ 未写回本地 Markdown")
                st.success("".join(parts))
            else:
                parts = ["❌ 更新失败"]
                if result["error_code"]:
                    parts.append(f"\n\n**错误代码：**`{result['error_code']}`")
                if result["error_message"]:
                    parts.append(f"\n\n**错误信息：**{result['error_message']}")
                if result["http_status"]:
                    parts.append(f"\n\n**HTTP 状态：**{result['http_status']}")
                st.error("".join(parts))


# =============================== MAIN ===================================

def main():
    st.set_page_config(page_title="AutoSite", page_icon="📝", layout="wide")
    st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

    config = load_config()
    if not config.validate():
        st.error(".env 配置不完整")
        st.info("复制 .env.example 为 .env 并填入正确的值。")
        st.stop()

    for k in ("wp_categories", "wp_tags", "wp_users"):
        st.session_state.setdefault(k, [])
    st.session_state.setdefault("auth_user", None)
    st.session_state.setdefault("c_dry_ok", False)
    st.session_state.setdefault("u_dry_ok", False)

    # ── Top bar ────────────────────────────────────────────────────
    top_left, top_right = st.columns([3, 1])
    with top_left:
        st.title("AutoSite — WordPress 发布工具")
        st.markdown(site_badge_html(config, st.session_state.auth_user), unsafe_allow_html=True)
    with top_right:
        if st.button("测试连接", use_container_width=True):
            client = make_client(config)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                user = client.check_auth()
            log = buf.getvalue()
            if user:
                st.session_state.auth_user = user
                st.success(f"{user.get('name', '')} · " + ", ".join(user.get("roles", [])))
            else:
                st.session_state.auth_user = None
                for l in log.splitlines():
                    l = l.strip()
                    if l:
                        st.caption(l.replace("[ERROR]", "❌").replace("[HINT]", "💡"))
            st.session_state.wp_users = []
            st.rerun()

        if st.button("加载分类/标签/用户", use_container_width=True, disabled=st.session_state.auth_user is None):
            client = make_client(config)
            with st.spinner("加载中..."):
                st.session_state.wp_categories = client.list_categories() or []
                st.session_state.wp_tags = client.list_tags() or []
                st.session_state.wp_users = client.list_users() or []
            st.rerun()

        st.caption(f"分类 {len(st.session_state.wp_categories)} / 标签 {len(st.session_state.wp_tags)}")

    st.divider()

    # ── Two tabs ────────────────────────────────────────────────────
    raw_count = len(raw_files())
    pub_count = len(published_files())
    tab_raw, tab_pub = st.tabs([f"📝 新文章发布 (raw)  [{raw_count}]", f"🔄 已发布文章更新 (published)  [{pub_count}]"])

    with tab_raw:
        page_create(config)

    with tab_pub:
        page_update(config)


if __name__ == "__main__":
    main()
