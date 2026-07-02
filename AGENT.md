从零开始创建一个项目

## 一、项目最终目标

我要做一个 Windows 本地 Markdown 上传工具。

最终使用方式：

1. 用户在 Windows 文件资源管理器中右键一个 `.md` 文件。
2. 右键菜单中出现：
   `上传到 threcial.cn`
3. 点击后自动上传该 Markdown 文件到 WordPress 网站 `threcial.cn`。
4. 程序自动判断这是新文章还是已有文章：

   * 新文章：创建 WordPress 文章
   * 已有文章：更新 WordPress 文章
5. 上传成功后，程序会把 WordPress 返回的 `wp_post_id`、`slug`、`wp_link` 等信息写回本地 Markdown 的 Front Matter。
6. 上传完成后弹出提示框，显示上传成功或失败。
7. 所有配置都由一个 `config.yaml` 完成，不需要 UI，不需要命令行交互。

不要做 Streamlit UI、Web UI、Electron、数据库、批量同步、DeepSeek 自动写文章。第一版只做“单个 Markdown 文件右键上传”。

---

## 二、技术栈

使用 Python 3。

推荐依赖：

```text
requests
PyYAML
markdown
beautifulsoup4
```

右键菜单使用 PowerShell 写入 Windows 当前用户注册表，不要求管理员权限。

弹窗使用 Python 内置 `tkinter.messagebox`，尽量不要增加额外 GUI 依赖。

---

## 三、目录结构

请从零创建以下目录结构：

```text
autosite-md-uploader/
├── AGENT.md
├── README.md
├── config.example.yaml
├── config.yaml
├── requirements.txt
├── .gitignore
├── src/
│   └── autosite/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── markdown_parser.py
│       ├── frontmatter.py
│       ├── wordpress_client.py
│       ├── uploader.py
│       ├── state.py
│       ├── logger.py
│       ├── notifier.py
│       └── utils.py
├── scripts/
│   ├── install_context_menu.ps1
│   ├── uninstall_context_menu.ps1
│   ├── upload_md.ps1
│   └── upload_md.bat
├── logs/
└── state/
```

要求：

1. `config.yaml` 是真实配置文件，不提交 Git。
2. `config.example.yaml` 是示例配置，可以提交。
3. `logs/` 自动创建。
4. `state/` 自动创建。
5. 所有敏感信息不能写入日志。

---

## 四、配置文件

创建 `config.example.yaml`：

```yaml
site:
  name: "threcial.cn"
  base_url: "https://threcial.cn"
  api_base: "https://threcial.cn/wp-json/wp/v2"
  username: "api_writer"
  application_password: "xxxx xxxx xxxx xxxx xxxx xxxx"
  verify_ssl: true
  timeout: 30

defaults:
  status: "draft"
  author: 2
  categories: []
  tags: []
  excerpt: ""
  auto_create_categories: false
  auto_create_tags: true

upload:
  write_back: true
  backup_before_write: true
  standardize_frontmatter: true
  title_match_enabled: true
  title_match_strict: true
  allow_publish_status: false
  update_detection_order:
    - "wp_post_id"
    - "slug"
    - "state"
    - "title_exact_match"

markdown:
  convert_to_html: true
  first_h1_as_title: true
  remove_first_h1_from_content: false
  extensions:
    - "extra"
    - "tables"
    - "fenced_code"
    - "codehilite"
    - "toc"
    - "sane_lists"

notification:
  enabled: true
  success_popup: true
  error_popup: true

logs:
  history_file: "logs/upload-history.jsonl"
  latest_file: "logs/upload-latest.json"

state:
  file: "state/state.json"
```

程序读取 `config.yaml`。

要求：

1. 如果 `config.yaml` 不存在，提示用户复制 `config.example.yaml`。
2. 不使用 `.env`。
3. 不在日志、控制台、弹窗中显示 `application_password`。
4. 修改 `config.yaml` 后即可改变程序行为。

---

## 五、CLI 命令

实现以下命令：

```bash
python -m autosite check
```

作用：

1. 检查 `config.yaml` 是否存在。
2. 检查 WordPress REST API 是否可访问。
3. 检查 `/wp-json/wp/v2/users/me` 认证是否成功。
4. 输出当前认证用户 ID、用户名、站点地址。

---

```bash
python -m autosite upload "D:\articles\test.md"
```

作用：

1. 上传指定 Markdown 文件。
2. 自动判断 create 或 update。
3. 标准化 Front Matter。
4. Markdown 转 HTML。
5. 调用 WordPress REST API。
6. 写回 Markdown。
7. 更新本地 state。
8. 写入日志。
9. 弹窗提示结果。

---

```bash
python -m autosite upload "D:\articles\test.md" --dry-run
```

作用：

1. 不真正上传。
2. 不写回 Markdown。
3. 不更新 state。
4. 不上传图片。
5. 输出将要执行的动作、最终 Front Matter、WordPress payload。

---

```bash
python -m autosite install-context-menu
```

作用：安装 Windows 右键菜单。

---

```bash
python -m autosite uninstall-context-menu
```

作用：卸载 Windows 右键菜单。

---

## 六、右键菜单

实现 Windows 右键菜单：

菜单名称：

```text
上传到 threcial.cn
```

只对 `.md` 文件显示。

安装脚本：

```powershell
scripts/install_context_menu.ps1
```

卸载脚本：

```powershell
scripts/uninstall_context_menu.ps1
```

右键菜单调用：

```powershell
scripts/upload_md.ps1 "%1"
```

`upload_md.ps1` 再调用：

```bash
python -m autosite upload "传入的md文件路径"
```

要求：

1. 支持中文路径。
2. 支持路径中有空格。
3. 不要求管理员权限。
4. 使用当前用户注册表 HKCU。
5. 安装后右键 `.md` 文件能看到“上传到 threcial.cn”。
6. 上传结束后弹窗提示成功或失败。
7. PowerShell 脚本要能自动定位项目根目录。

建议注册表路径：

```text
HKCU:\Software\Classes\SystemFileAssociations\.md\shell\UploadToThrecial
```

---

## 七、Markdown Front Matter 处理

Markdown 可能有三种情况。

### 1. 没有 Front Matter

例如：

```markdown
# Nginx 配置说明

正文内容。
```

程序需要自动补全 Front Matter。

规则：

1. `title` 优先取第一个一级标题 `# xxx`。
2. 如果没有一级标题，使用文件名作为标题。
3. `status` 使用 `config.yaml` 中 `defaults.status`。
4. `author` 使用 `defaults.author`。
5. `categories` 使用 `defaults.categories`。
6. `tags` 使用 `defaults.tags`。
7. `excerpt` 使用 `defaults.excerpt`。
8. 不要在本地生成 slug。

标准化后类似：

```markdown
---
title: "Nginx 配置说明"
status: "draft"
categories: []
tags: []
author: 2
excerpt: ""
---

# Nginx 配置说明

正文内容。
```

### 2. Front Matter 不完整

例如：

```markdown
---
title: "Linux 防火墙配置"
tags:
  - "firewalld"
---

正文内容。
```

程序需要补全缺失字段，但不能覆盖用户已有字段。

补全后：

```markdown
---
title: "Linux 防火墙配置"
status: "draft"
categories: []
tags:
  - "firewalld"
author: 2
excerpt: ""
---

正文内容。
```

### 3. 已经发布过

例如：

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

程序应自动识别为已有文章，执行 update。

---

## 八、标准 Front Matter 字段

标准字段如下：

```yaml
title: "文章标题"
slug: "wordpress-returned-slug"
wp_post_id: 123
wp_link: "https://threcial.cn/example/"
status: "draft"
categories:
  - "Linux"
tags:
  - "Nginx"
author: 2
excerpt: ""
cover: ""
date: ""
last_published_at: "2026-06-29 13:30:00"
last_updated_at: "2026-06-29 14:10:00"
last_uploaded_at: "2026-06-29 14:10:00"
```

说明：

1. `slug` 由 WordPress 返回。
2. `wp_post_id` 是最优先的更新依据。
3. `wp_link` 是 WordPress 返回链接。
4. `last_published_at` 只在首次创建时写入。
5. `last_updated_at` 只在更新时写入。
6. `last_uploaded_at` 每次成功上传都更新。
7. `date` 用于定时发布。
8. `cover` 用于封面图。
9. 不要本地生成 slug。

---

## 九、创建还是更新的判断逻辑

新增函数：

```python
determine_action(file_path, frontmatter, state, config)
```

判断顺序：

### 1. wp_post_id

如果 Front Matter 中有：

```yaml
wp_post_id: 123
```

直接 update：

```http
POST /wp-json/wp/v2/posts/123
```

### 2. slug

如果有：

```yaml
slug: "nginx-config"
```

调用：

```http
GET /wp-json/wp/v2/posts?slug=nginx-config
```

如果查到文章，update。

如果查不到，fallback 为 create，并记录日志。

### 3. state

如果 `state/state.json` 中记录当前文件对应的 `post_id`，执行 update。

### 4. title_exact_match

如果配置启用：

```yaml
title_match_enabled: true
```

则通过 WordPress 搜索标题：

```http
GET /wp-json/wp/v2/posts?search=标题
```

然后对返回结果中的标题做严格文本匹配。

要求：

1. 只匹配到一篇文章时，执行 update。
2. 匹配不到时，执行 create。
3. 匹配到多篇时，不自动上传，提示用户手动补充 `wp_post_id` 或 `slug`。
4. 标题匹配只作为最后兜底，不能优先于 `wp_post_id` 和 `slug`。

---

## 十、创建文章流程

当判断为 create：

1. 标准化 Front Matter。
2. Markdown 转 HTML。
3. 解析分类和标签名称为 WordPress ID。
4. 如果分类不存在：

   * `auto_create_categories=true` 时创建分类。
   * 否则报错。
5. 如果标签不存在：

   * `auto_create_tags=true` 时创建标签。
   * 否则报错。
6. 创建文章 payload 不要传空 slug。
7. 本地没有 slug 时，不传 slug，让 WordPress 自动生成。
8. 调用：

   ```http
   POST /wp-json/wp/v2/posts
   ```
9. 成功后读取：

   * `id`
   * `slug`
   * `link`
   * `status`
10. 写回 Markdown：

* `wp_post_id`
* `slug`
* `wp_link`
* `status`
* `last_published_at`
* `last_uploaded_at`

11. 更新 `state/state.json`。
12. 写入日志。
13. 弹窗提示成功。

---

## 十一、更新文章流程

当判断为 update：

1. 标准化 Front Matter。
2. Markdown 转 HTML。
3. 解析分类和标签名称为 WordPress ID。
4. 构造 update payload。
5. 调用：

   ```http
   POST /wp-json/wp/v2/posts/{wp_post_id}
   ```
6. 支持更新：

   * `title`
   * `content`
   * `status`
   * `categories`
   * `tags`
   * `author`
   * `excerpt`
   * `featured_media`
   * `date`
7. 如果 Front Matter 中没有某字段，不主动清空 WordPress 上的字段。
8. 如果 Front Matter 中明确写了 `categories: []`，表示清空分类。
9. 如果 Front Matter 中明确写了 `tags: []`，表示清空标签。
10. 默认不修改 slug。
11. 只有 Front Matter 明确写了：

    ```yaml
    slug_update: true
    slug: "new-slug"
    ```

    才允许向 WordPress 提交 slug。
12. 更新成功后读取：

    * `id`
    * `slug`
    * `link`
    * `status`
13. 写回 Markdown：

    * `wp_post_id`
    * `slug`
    * `wp_link`
    * `status`
    * `last_updated_at`
    * `last_uploaded_at`
14. 更新 `state/state.json`。
15. 写入日志。
16. 弹窗提示成功。

---

## 十二、状态保护

默认使用草稿。

如果配置中：

```yaml
upload:
  allow_publish_status: false
```

则即使 Markdown 里写了：

```yaml
status: "publish"
```

也要降级为：

```yaml
status: "draft"
```

并在日志中记录警告：

```text
publish status blocked by config, downgraded to draft
```

只有当：

```yaml
allow_publish_status: true
```

才允许通过接口直接发布。

---

## 十三、Markdown 转 HTML

WordPress 的 `content` 字段必须提交 HTML，不要直接提交 Markdown。

使用 `markdown` 包转换：

```python
markdown.markdown(
    content,
    extensions=[
        "extra",
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "sane_lists"
    ],
    output_format="html5"
)
```

要求支持：

1. 标题
2. 段落
3. 列表
4. 表格
5. 代码块
6. 引用
7. 链接
8. 图片

---

## 十四、图片和封面图

第一版可以支持封面图和正文图片上传。

如果 Front Matter 中有：

```yaml
cover: "./cover.jpg"
```

则上传到 WordPress 媒体库，并将返回的媒体 ID 设置为：

```json
{
  "featured_media": 123
}
```

Markdown 正文中的本地图片，例如：

```markdown
![架构图](./images/arch.png)
```

应上传到 WordPress 媒体库，并替换为 WordPress 图片 URL。

要求：

1. 支持相对路径。
2. 支持绝对路径。
3. 支持 jpg、jpeg、png、webp、gif。
4. 图片不存在时停止上传。
5. 图片上传失败时停止上传。
6. 成功上传后记录到 state，避免重复上传同一张图片。
7. 不要把本地图片路径发布到 WordPress。

---

## 十五、本地 state

维护：

```text
state/state.json
```

示例：

```json
{
  "files": {
    "D:/articles/a.md": {
      "post_id": 123,
      "slug": "a",
      "link": "https://threcial.cn/a/",
      "last_hash": "sha256:xxxx",
      "last_uploaded_at": "2026-06-29 15:30:00"
    }
  },
  "media": {
    "D:/articles/images/arch.png": {
      "media_id": 456,
      "url": "https://threcial.cn/wp-content/uploads/2026/06/arch.png",
      "last_hash": "sha256:yyyy"
    }
  }
}
```

要求：

1. state 文件不存在时自动创建。
2. state 文件损坏时备份为 `.broken`，然后重建。
3. 成功 create / update 后更新 state。
4. 成功上传媒体后更新 media 记录。
5. 写 state 时使用临时文件原子替换。

---

## 十六、日志

每次上传都写入：

```text
logs/upload-history.jsonl
```

成功示例：

```json
{"time":"2026-06-29 15:30:00","action":"create","success":true,"source":"D:/articles/a.md","post_id":123,"slug":"a","link":"https://threcial.cn/a/","status":"draft"}
```

失败示例：

```json
{"time":"2026-06-29 16:05:00","action":"create","success":false,"source":"D:/articles/b.md","error_code":"rest_cannot_create","error_message":"Sorry, you are not allowed to create posts as this user.","http_status":403}
```

同时写入最新结果：

```text
logs/upload-latest.json
```

要求：

1. 成功和失败都记录。
2. 日志中不能包含 Application Password。
3. 日志中不能包含 Authorization Header。
4. 失败时保留 WordPress 返回的 `code`、`message`、`status`。
5. 写日志前自动创建 logs 目录。

---

## 十七、弹窗提示

使用 `tkinter.messagebox`。

成功弹窗：

```text
上传成功

动作：创建新文章
标题：Nginx 配置说明
文章 ID：123
Slug：nginx-config
状态：draft
链接：https://threcial.cn/nginx-config/
```

更新成功弹窗：

```text
上传成功

动作：更新文章
标题：Nginx 配置说明
文章 ID：123
Slug：nginx-config
状态：draft
链接：https://threcial.cn/nginx-config/
```

失败弹窗：

```text
上传失败

文件：D:\articles\a.md
错误：403 rest_cannot_create
说明：当前 WordPress 用户没有创建文章权限。
```

要求：

1. 成功和失败都弹窗。
2. 命令行也输出同样结果。
3. 如果 `notification.enabled=false`，则不弹窗，只输出 CLI 和日志。

---

## 十八、写回 Markdown

上传成功后写回本地 Markdown Front Matter。

要求：

1. 只更新 Front Matter。
2. 保留正文内容。
3. 不破坏 Markdown 格式。
4. 写回前如果配置 `backup_before_write=true`，创建 `.bak` 备份。
5. 使用临时文件原子替换，避免写入失败损坏原文件。
6. dry-run 模式不写回。

---

## 十九、错误处理

必须处理：

1. 文件不存在。
2. 文件不是 `.md`。
3. `config.yaml` 不存在。
4. WordPress REST API 不可达。
5. 认证失败 401。
6. 权限不足 403。
7. 分类不存在且不允许自动创建。
8. 标签不存在且不允许自动创建。
9. Front Matter YAML 格式错误。
10. Markdown 解析失败。
11. 图片不存在。
12. 图片上传失败。
13. WordPress 500。
14. 网络超时。
15. 创建成功但写回 Markdown 失败。
16. state 文件损坏。
17. 标题匹配到多篇文章。

错误信息必须清晰，适合普通用户理解。

---

## 二十、安全要求

1. 不使用 `xmlrpc.php`。
2. 不使用 Selenium。
3. 不自动登录 WordPress 后台。
4. 只使用 WordPress REST API。
5. 不输出 Application Password。
6. 不输出 Authorization Header。
7. `config.yaml` 加入 `.gitignore`。
8. 默认发布状态是 `draft`。
9. 直接发布 `publish` 必须由 `config.yaml` 显式允许。

---

## 二十一、README 要求

生成 README.md，包含：

1. 项目用途。
2. 安装 Python 依赖。
3. 如何创建 `config.yaml`。
4. 如何测试 WordPress 连接。
5. 如何安装右键菜单。
6. 如何卸载右键菜单。
7. 如何上传 Markdown。
8. Front Matter 示例。
9. 常见错误说明：

   * 401
   * 403
   * 分类创建失败
   * 标签创建失败
   * 图片上传失败

---

## 二十二、验收标准

完成后必须满足：

1. `pip install -r requirements.txt` 成功。
2. `python -m autosite check` 可以验证 WordPress 认证。
3. 右键 `.md` 文件能看到“上传到 threcial.cn”。
4. 点击右键菜单可以上传当前 `.md` 文件。
5. 无 Front Matter 的 Markdown 可以自动补全格式头。
6. 不完整 Front Matter 可以自动标准化。
7. 新文章可以 create。
8. 已有 `wp_post_id` 的文章可以 update。
9. 已有 `slug` 且远程存在的文章可以 update。
10. 创建成功后写回 `wp_post_id`、`slug`、`wp_link`、`last_published_at`。
11. 更新成功后写回 `last_updated_at`、`last_uploaded_at`。
12. 上传成功弹窗显示 ID、slug、link。
13. 上传失败弹窗显示错误原因。
14. 日志写入 `logs/upload-history.jsonl`。
15. 最新结果写入 `logs/upload-latest.json`。
16. 不泄露 Application Password。
17. 不需要启动 UI。
18. 不需要用户交互输入。

请先实现最小可用版本：

1. 配置读取
2. check
3. Markdown Front Matter 标准化
4. Markdown 转 HTML
5. create / update 判断
6. WordPress 创建文章
7. WordPress 更新文章
8. 写回 Markdown
9. 日志
10. 弹窗
11. 右键菜单安装和卸载

完成最小可用版本后，再实现图片上传。
