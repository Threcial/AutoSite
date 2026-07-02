import sys

try:
    import tkinter
    import tkinter.messagebox
    _HAS_TK = True
except ImportError:
    _HAS_TK = False


def notify_success(action_label, title, post_id, slug, status, link):
    msg = (
        f"动作：{action_label}\n"
        f"标题：{title}\n"
        f"文章 ID：{post_id}\n"
        f"Slug：{slug}\n"
        f"状态：{status}\n"
        f"链接：{link}"
    )
    print(f"[SUCCESS] {action_label}")
    print(f"  标题：{title}")
    print(f"  文章 ID：{post_id}")
    print(f"  Slug：{slug}")
    print(f"  状态：{status}")
    print(f"  链接：{link}")
    if _HAS_TK:
        tkinter.messagebox.showinfo("上传成功", msg)


def notify_failure(filepath, http_status, error_code, error_message):
    msg = (
        f"文件：{filepath}\n"
        f"错误：{http_status} {error_code}\n"
        f"说明：{error_message}"
    )
    print(f"[ERROR] Upload failed: {filepath}")
    print(f"  HTTP {http_status} {error_code}")
    print(f"  {error_message}")
    if _HAS_TK:
        tkinter.messagebox.showerror("上传失败", msg)
