# AutoSite — Markdown 右键上传到 WordPress

在 Windows 文件资源管理器中右键 `.md` 文件，一键上传到 WordPress 网站（创建或更新文章），自动处理 Front Matter、Markdown 转 HTML、分类标签、封面图、正文图片、弹窗通知、日志记录。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 右键上传 | 安装后在 `.md` 文件右键菜单中显示「上传到 threcial.cn」 |
| 自动创建/更新 | 根据 `wp_post_id` / `slug` / 本地 state / 标题匹配 判断 |
| Front Matter 标准化 | 自动补全缺失字段，保留已有字段 |
| Markdown 转 HTML | 支持 extra、tables、fenced_code 等扩展 |
| 分类/标签 | 按名称解析为 WordPress ID，支持自动创建 |
| 图片上传 | 正文图片和封面图上传播到 WordPress 媒体库 |
| 弹窗通知 | 上传成功或失败弹出 Windows 消息框 |
| 日志记录 | history.jsonl（历史记录） + latest.json（最新结果） |
| 本地 state 管理 | 记录文件与 post_id / 图片与 media_id 的映射 |
| 草稿保护 | 默认发布为 draft，需显式配置才允许 publish |
| 预览模式 | `--dry-run` 预览 payload，不修改任何文件 |

---

## 安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

依赖列表：`requests`、`PyYAML`、`markdown`、`beautifulsoup4`

### 2. 配置 WordPress 连接

复制配置文件：

```bash
copy config.example.yaml config.yaml
```

编辑 `config.yaml`，填写 WordPress 站点信息（见下方配置说明）。

### 3. 安装开发模式（可选）

如果遇到 `No module named autosite` 错误，执行：

```bash
pip install -e .
```

### 4. 验证连接

```bash
python -m autosite check
```

成功输出示例：

```
[INFO] WordPress: https://threcial.cn
[INFO] Checking connection and authentication...
[INFO] Authentication successful
[INFO] User ID:   2
[INFO] Username:  atri
[INFO] Display:   超管
[INFO] Site URL:  https://threcial.cn
```

---

## CLI 命令

### `python -m autosite check`

检查 WordPress REST API 是否可访问、认证是否成功，输出当前用户信息。

### `python -m autosite upload <文件路径>`

上传指定 Markdown 文件到 WordPress。

流程：
1. 读取 Markdown，解析 Front Matter
2. 标准化 Front Matter（补全缺失字段）
3. Markdown 正文转 HTML
4. 判断是创建还是更新（见下方判断逻辑）
5. 解析分类、标签名称为 WordPress ID
6. 上传正文中的本地图片到 WordPress 媒体库
7. 上传封面图到 WordPress 媒体库（可选）
8. 调用 WordPress REST API 创建或更新文章
9. 写回 WordPress 返回的 `wp_post_id`、`slug`、`wp_link` 等到本地 Front Matter
10. 更新本地 state / 写入日志 / 弹窗通知

```bash
python -m autosite upload "D:\我的文章\Linux 配置.md"
```

### `python -m autosite upload <文件路径> --dry-run`

预览模式——不执行任何写操作：

- 不调用 WordPress API
- 不写回 Markdown
- 不更新 state
- 不上传图片
- 仅输出推断的动作、最终 Front Matter、WordPress payload

```bash
python -m autosite upload "test.md" --dry-run
```

### `python -m autosite install-context-menu`

安装 Windows 右键菜单。

安装后，在文件资源管理器中右键任意 `.md` 文件 → 菜单显示「上传到 threcial.cn」。

注册表路径（当前用户，无需管理员权限）：
```
HKCU:\Software\Classes\SystemFileAssociations\.md\shell\UploadToThrecial
```

### `python -m autosite uninstall-context-menu`

卸载 Windows 右键菜单，删除上述注册表路径。

---

## 图形配置工具

AutoSite 提供 Windows 本地 GUI 配置工具，用于直观编辑 `config.yaml`、测试连接、安装/卸载右键菜单。

### 启动方式

```bash
python -m autosite gui
```

或双击项目目录下的：

- `scripts/start_gui.bat`
- `scripts/start_gui.ps1`

### GUI 功能

| 页面 | 功能 |
|------|------|
| 站点配置 | 编辑站点名称、URL、API 地址、用户名、密码（密码框显示+显示/隐藏）、SSL、超时；一键测试连接 |
| 默认文章配置 | 设置默认 status（下拉框）、author、categories/tags（多行文本）、excerpt、自动创建 |
| 上传行为 | 写回、备份、Front Matter 标准化、标题匹配、publish 权限、更新检测顺序（多行编辑+校验） |
| Markdown 设置 | 转 HTML、H1 作为标题、移除 H1、扩展列表 |
| 通知与日志 | 弹窗开关、日志路径；快速打开历史日志/最新结果/state 文件/目录 |
| 右键菜单 | 安装、卸载、检查状态 |
| 工具 | 测试连接、选择 Markdown 文件 dry-run、打开 config.yaml / 项目目录 / README |

### 保存配置

- 保存前自动备份 `config.yaml.bak`
- 使用临时文件原子替换写入（不会写坏原文件）
- 保存时校验更新检测顺序字段合法性

---

## 配置说明

配置文件 `config.yaml` 所有字段及说明：

```yaml
site:
  name: "threcial.cn"                        # 站点名称（仅显示用）
  base_url: "https://threcial.cn"            # WordPress 站点地址
  api_base: "https://threcial.cn/wp-json/wp/v2"  # REST API 地址
  username: "api_writer"                     # WordPress 用户名
  application_password: "xxxx xxxx xxxx xxxx xxxx xxxx"  # Application Password
  verify_ssl: true                           # 是否验证 SSL 证书
  timeout: 30                                # HTTP 请求超时（秒）

defaults:
  status: "draft"                            # 默认发布状态（draft / publish）
  author: 2                                  # 默认作者 ID
  categories: []                             # 默认分类名称列表
  tags: []                                   # 默认标签名称列表
  excerpt: ""                                # 默认摘要
  auto_create_categories: false              # 分类不存在时自动创建
  auto_create_tags: true                     # 标签不存在时自动创建

upload:
  write_back: true                           # 上传成功后写回 Markdown Front Matter
  backup_before_write: true                  # 写回前创建 .bak 备份
  standardize_frontmatter: true              # 上传前标准化 Front Matter
  title_match_enabled: true                  # 允许通过标题匹配查找已有文章
  title_match_strict: true                   # 标题必须严格相等才匹配
  allow_publish_status: false                # 是否允许发布为 publish（false 则强制降级为 draft）
  update_detection_order:                    # 检测更新方式的优先级顺序
    - "wp_post_id"
    - "slug"
    - "state"
    - "title_exact_match"

markdown:
  convert_to_html: true                      # Markdown 转 HTML 后提交
  first_h1_as_title: true                    # 取第一个 # 标题作为文章标题
  remove_first_h1_from_content: false        # 从正文中移除第一个 # 标题
  extensions:
    - "extra"
    - "tables"
    - "fenced_code"
    - "codehilite"
    - "toc"
    - "sane_lists"

notification:
  enabled: true                              # 启用弹窗通知
  success_popup: true                        # 成功时弹窗
  error_popup: true                          # 失败时弹窗

logs:
  history_file: "logs/upload-history.jsonl"   # 历史记录日志文件
  latest_file: "logs/upload-latest.json"      # 最近一次上传结果

state:
  file: "state/state.json"                   # 本地状态文件
```

### 安全说明

- `application_password` **不会**出现在日志、控制台输出、弹窗中
- `config.yaml` 已在 `.gitignore` 中，不会被提交到 Git
- 默认发布状态为 `draft`，避免误发布
- 如需直接发布，设置 `allow_publish_status: true`

---

## Front Matter 规范

### 标准字段

```yaml
---
title: "文章标题"                    # 文章标题
slug: "wordpress-returned-slug"      # WordPress 返回的 slug（不手动设置）
wp_post_id: 123                      # WordPress 文章 ID（不手动设置）
wp_link: "https://threcial.cn/example/"  # WordPress 文章链接（不手动设置）
status: "draft"                      # 发布状态
categories:                          # 分类名称列表
  - "Linux"
tags:                                # 标签名称列表
  - "Nginx"
author: 2                            # 作者 ID
excerpt: ""                          # 文章摘要
cover: ""                            # 封面图路径（本地相对/绝对路径或 URL）
date: ""                             # 定时发布日期（如 2026-07-03T10:00:00）
last_published_at: "2026-06-29 13:30:00"  # 首次发布时间（自动写入）
last_updated_at: "2026-06-29 14:10:00"    # 最后更新时间（自动写入）
last_uploaded_at: "2026-06-29 14:10:00"   # 最后上传时间（自动写入）
---
```

### 三种 Front Matter 场景

**1. 没有 Front Matter**

```markdown
# Nginx 配置说明

正文内容。
```

程序自动补全 —— `title` 取第一个 `# 标题`，其他字段取配置默认值。

**2. Front Matter 不完整**

```markdown
---
title: "Linux 防火墙配置"
tags:
  - "firewalld"
---

正文内容。
```

程序补全缺失字段（status、categories、author、excerpt），保留已有字段。

**3. 已经发布过的文章**

```markdown
---
title: "Nginx 配置说明"
slug: "nginx-config"
wp_post_id: 123
wp_link: "https://threcial.cn/nginx-config/"
status: "draft"
categories:
  - "Linux"
tags:
  - "Nginx"
author: 2
last_published_at: "2026-06-29 13:30:00"
---

正文内容。
```

程序自动识别为已有文章（通过 `wp_post_id`），执行更新操作。上传成功后自动更新 `slug`、`wp_link`、`status`、`last_updated_at`、`last_uploaded_at`。

---

## 创建 vs 更新判断逻辑

按配置 `update_detection_order` 的顺序依次检查：

| 优先级 | 检测方式 | 条件 |
|--------|----------|------|
| 1 | `wp_post_id` | Front Matter 中存在 `wp_post_id` → 直接调用 `POST /posts/{id}` |
| 2 | `slug` | Front Matter 中存在 `slug` → 查询 WordPress 是否存在该 slug → 存在则 update |
| 3 | `state` | `state/state.json` 中记录该文件对应的 post_id → 执行 update |
| 4 | `title_exact_match` | 通过 WordPress 搜索标题 → 匹配到 1 篇则 update，多篇则报错 |

全部不匹配则执行创建操作。

---

## 日志

每次上传写入 `logs/upload-history.jsonl`（追加）：

```json
{"time":"2026-06-29 15:30:00","action":"create","success":true,"source":"D:/articles/a.md","post_id":123,"slug":"a","link":"https://threcial.cn/a/","status":"draft"}
```

同时覆盖写入 `logs/upload-latest.json`（最新结果）。

失败记录保留 WordPress 返回的 `error_code`、`error_message`、`http_status`：

```json
{"time":"2026-06-29 16:05:00","action":"create","success":false,"source":"D:/articles/b.md","error_code":"rest_cannot_create","error_message":"Sorry, you are not allowed to create posts as this user.","http_status":403}
```

---

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| 401 | Application Password 错误 | 检查 `config.yaml` 中的 `username` 和 `application_password` |
| 403 | 当前用户没有创建/编辑文章权限 | 在 WordPress 后台检查用户角色权限 |
| rest_category_not_found | 分类不存在 | 设置 `auto_create_categories: true` 或手动创建分类 |
| rest_tag_not_found | 标签不存在 | 设置 `auto_create_tags: true` 或手动创建标签 |
| 图片上传失败 | 本地图片路径错误或 WordPress 媒体库异常 | 检查图片路径和 WordPress 媒体库设置 |
| 标题匹配到多篇文章 | 标题不唯一 | 在 Front Matter 中添加 `wp_post_id` 或 `slug` 来指定文章 |
| 网络超时 | WordPress 服务器无响应 | 检查网络连接，或增加 `timeout` 值 |
