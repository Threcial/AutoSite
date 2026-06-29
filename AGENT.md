# AGENT.md

## 项目目标

本项目用于创建一个本地自动化发布流程，将本地文章内容通过 WordPress REST API 发布到 WordPress 站点。

目标功能：

1. 从本地 Markdown / JSON 文件读取文章内容。
2. 自动处理文章标题、正文、摘要、别名、状态、分类、标签、作者、封面图等属性。
3. 通过 WordPress REST API 创建或更新文章。
4. 支持草稿、直接发布、定时发布。
5. 支持自动创建不存在的分类和标签。
6. 支持上传封面图并设置为特色图片。
7. 提供 dry-run 模式，发布前可预览请求内容。
8. 所有敏感信息必须通过 `.env` 配置，不得硬编码。

---

## 技术栈要求

优先使用：

* Python 3
* requests
* python-dotenv
* PyYAML
* markdown 或 markdown2

也可以使用 Shell，但核心发布逻辑建议使用 Python，便于处理 JSON、异常、重试、文件解析和日志。

---

## WordPress 接口说明

使用 WordPress REST API。

基础地址：

```text
https://example.com/wp-json/wp/v2
```

认证方式：

```text
Basic Auth
用户名：WordPress 用户名
密码：Application Password
```

注意：

* 不使用 `xmlrpc.php`
* 使用 `/wp-json/wp/v2/posts` 发布文章
* 使用 `/wp-json/wp/v2/categories` 管理分类
* 使用 `/wp-json/wp/v2/tags` 管理标签
* 使用 `/wp-json/wp/v2/media` 上传图片
* 使用 `/wp-json/wp/v2/users/me` 测试认证

---

## 环境变量

项目根目录需要支持 `.env` 文件。

示例：

```env
WP_BASE_URL=https://example.com
WP_USERNAME=api_writer
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
WP_DEFAULT_AUTHOR=1
WP_DEFAULT_STATUS=draft
WP_VERIFY_SSL=true
```

要求：

* `.env` 不允许提交到 Git。
* 必须提供 `.env.example`。
* 程序启动时要检查必要配置是否存在。
* `WP_APP_PASSWORD` 允许包含空格。
* URL 结尾是否带 `/` 都要兼容。

---

## 推荐目录结构

```text
wordpress-publisher/
├── AGENT.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── articles/
│   └── example.md
├── assets/
│   └── cover.jpg
├── logs/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── wordpress_client.py
│   ├── article_parser.py
│   ├── publisher.py
│   └── logger.py
└── tests/
```

---

## 文章文件格式

优先支持 Markdown + Front Matter。

示例：

```markdown
---
title: "接口发布测试文章"
slug: "api-post-test"
status: "draft"
categories:
  - "Linux运维"
  - "WordPress"
tags:
  - "Nginx"
  - "REST API"
author: 1
excerpt: "这是文章摘要"
cover: "assets/cover.jpg"
---

# 接口发布测试文章

这里是正文内容。

## 二级标题

正文可以使用 Markdown，发布前需要转换为 HTML。
```

字段说明：

| 字段         | 类型     | 说明                                 |
| ---------- | ------ | ---------------------------------- |
| title      | string | 文章标题，必填                            |
| content    | string | 文章正文，由 Markdown 正文转换               |
| status     | string | draft / publish / private / future |
| slug       | string | 文章别名                               |
| categories | list   | 分类名称列表，发布前转换成分类 ID                 |
| tags       | list   | 标签名称列表，发布前转换成标签 ID                 |
| author     | int    | WordPress 用户 ID                    |
| excerpt    | string | 文章摘要                               |
| cover      | string | 本地封面图路径                            |
| date       | string | 发布时间，定时发布时使用                       |

---

## 发布逻辑

创建文章接口：

```http
POST /wp-json/wp/v2/posts
```

更新文章接口：

```http
POST /wp-json/wp/v2/posts/{post_id}
```

创建文章时的 JSON 示例：

```json
{
  "title": "文章标题",
  "content": "<p>文章正文</p>",
  "status": "draft",
  "categories": [3, 8],
  "tags": [5, 9],
  "author": 1,
  "excerpt": "文章摘要",
  "slug": "article-slug",
  "featured_media": 123
}
```

规则：

1. `categories` 必须传分类 ID 数组。
2. `tags` 必须传标签 ID 数组。
3. `author` 必须传用户 ID。
4. `featured_media` 必须传媒体 ID。
5. 更新文章时，数组字段会覆盖原值，不是追加。
6. 默认先发布为 `draft`，除非文章或命令明确指定 `publish`。
7. 生产环境默认启用 dry-run，避免误发布。

---

## 分类处理逻辑

发布前需要将分类名称转换成分类 ID。

流程：

1. 请求 `/wp-json/wp/v2/categories?search=分类名`
2. 判断是否已有完全匹配的分类。
3. 如果存在，使用已有 ID。
4. 如果不存在，调用创建分类接口。
5. 创建成功后使用返回的 ID。

创建分类接口：

```http
POST /wp-json/wp/v2/categories
```

请求示例：

```json
{
  "name": "Linux运维",
  "slug": "linux-ops"
}
```

注意：

* 分类名称可能包含中文。
* slug 应自动生成，但不能生成非法字符。
* 如果 slug 冲突，应让 WordPress 自动处理或追加后缀。

---

## 标签处理逻辑

发布前需要将标签名称转换成标签 ID。

流程：

1. 请求 `/wp-json/wp/v2/tags?search=标签名`
2. 判断是否已有完全匹配的标签。
3. 如果存在，使用已有 ID。
4. 如果不存在，调用创建标签接口。
5. 创建成功后使用返回的 ID。

创建标签接口：

```http
POST /wp-json/wp/v2/tags
```

请求示例：

```json
{
  "name": "Nginx",
  "slug": "nginx"
}
```

---

## 封面图处理逻辑

如果文章 Front Matter 中存在 `cover` 字段：

1. 检查本地图片是否存在。
2. 判断文件类型。
3. 上传到 WordPress 媒体库。
4. 获取返回的媒体 ID。
5. 发布文章时传入 `featured_media`。

上传接口：

```http
POST /wp-json/wp/v2/media
```

请求头要求：

```http
Content-Disposition: attachment; filename=cover.jpg
Content-Type: image/jpeg
```

上传成功后返回 JSON 中的 `id` 即媒体 ID。

---

## 命令行要求

至少支持以下命令：

```bash
python src/main.py check
```

作用：

* 检查 `.env`
* 检查 WordPress REST API 是否可访问
* 检查认证是否成功
* 输出当前认证用户信息

---

```bash
python src/main.py publish articles/example.md --dry-run
```

作用：

* 解析文章
* 转换 Markdown 为 HTML
* 解析分类和标签
* 不真正发布
* 输出最终请求 JSON

---

```bash
python src/main.py publish articles/example.md
```

作用：

* 正式发布文章
* 默认状态优先使用文章 Front Matter 中的 `status`
* 如果未指定，使用 `.env` 中的 `WP_DEFAULT_STATUS`

---

```bash
python src/main.py update articles/example.md --post-id 123
```

作用：

* 更新指定 ID 的文章
* 不创建新文章

---

## 错误处理要求

必须对常见错误做明确提示。

### 401 Unauthorized

提示方向：

* 用户名错误
* Application Password 错误
* Nginx 未传递 Authorization 头
* WordPress 安全插件拦截 REST API

### 403 Forbidden

提示方向：

* 当前 WordPress 用户权限不足
* 用户不是 Author / Editor / Administrator
* 无权发布或修改他人文章
* 无权创建分类、标签或上传媒体

### rest_cannot_create

提示：

* 当前用户没有创建文章权限

### rest_cannot_publish

提示：

* 当前用户可以创建草稿，但没有直接发布权限

### 413 Request Entity Too Large

提示：

* 图片或正文过大
* 需要检查 Nginx `client_max_body_size`

### PHP memory exhausted

提示：

* WordPress 插件、主题、autoload、缓存可能异常
* 不是客户端程序问题

---

## 日志要求

程序需要输出清晰日志。

日志至少包含：

* 当前操作类型
* 文章文件路径
* WordPress 站点地址
* 是否 dry-run
* 分类名称到 ID 的映射
* 标签名称到 ID 的映射
* 上传媒体 ID
* 创建或更新后的文章 ID
* WordPress 返回的错误信息

不要在日志中输出：

* Application Password
* Authorization Header
* `.env` 完整内容

---

## 安全要求

严格禁止：

1. 在代码中硬编码 WordPress 密码。
2. 在日志中打印认证信息。
3. 默认直接发布到 `publish`。
4. 未确认文章内容时批量发布。
5. 使用 `xmlrpc.php`。
6. 将 `.env`、日志、缓存文件提交到 Git。
7. 忽略 HTTP 状态码。
8. 吞掉 WordPress 返回的错误信息。

---

## 幂等性要求

如果文章 Front Matter 中存在 `slug`，发布前应支持按 slug 查询是否已存在文章。

查询方式：

```http
GET /wp-json/wp/v2/posts?slug=article-slug
```

推荐逻辑：

1. 如果启用 `--upsert`：

   * slug 存在：更新已有文章
   * slug 不存在：创建新文章
2. 如果未启用 `--upsert`：

   * 直接创建新文章
3. 如果 slug 已存在但用户没有指定 `--upsert`：

   * 给出警告，避免重复发布

---

## 批量发布要求

后续可以支持批量发布：

```bash
python src/main.py publish-dir articles/ --dry-run
python src/main.py publish-dir articles/
```

批量发布要求：

1. 默认必须 dry-run。
2. 正式发布前列出待发布文章数量。
3. 单篇失败不能导致全部中断，除非指定 `--fail-fast`。
4. 输出成功、失败、跳过的统计结果。
5. 每篇文章都要有独立日志。

---

## 代码质量要求

实现时必须：

1. 函数职责清晰。
2. WordPress API 调用集中在 `wordpress_client.py`。
3. 文件解析集中在 `article_parser.py`。
4. 发布流程集中在 `publisher.py`。
5. 不把所有逻辑写在一个文件里。
6. HTTP 请求必须设置 timeout。
7. 对网络错误、JSON 解析错误、文件不存在做异常处理。
8. 输出给用户的错误信息必须可读。
9. 不生成过度复杂的抽象。
10. 保持代码可直接运行和维护。

---

## 最小可用版本优先级

第一阶段只实现：

1. 读取 `.env`
2. 测试认证
3. 读取单篇 Markdown
4. 发布草稿文章
5. 指定分类、标签、作者
6. 上传封面图
7. dry-run

第二阶段再实现：

1. upsert
2. 批量发布
3. 定时发布
4. 更完整的日志
5. 单元测试
6. 发布结果记录

---

## 验收标准

完成后需要满足：

1. `python src/main.py check` 可以成功验证 WordPress 认证。
2. `python src/main.py publish articles/example.md --dry-run` 可以输出正确 JSON。
3. `python src/main.py publish articles/example.md` 可以创建 WordPress 草稿。
4. 分类名称可以自动转换为 ID。
5. 标签名称可以自动转换为 ID。
6. 不存在的分类和标签可以自动创建。
7. 本地封面图可以上传并设置为特色图片。
8. 错误认证时能清楚提示 401。
9. 权限不足时能清楚提示 403。
10. 日志中不会泄露 Application Password。

---

## 实现时优先考虑的用户体验

输出要直接、明确，适合运维人员排查。

示例输出：

```text
[INFO] Loading article: articles/example.md
[INFO] WordPress: https://example.com
[INFO] Dry run: true
[INFO] Category: Linux运维 -> ID 3
[INFO] Tag: Nginx -> ID 5
[INFO] Cover uploaded: assets/cover.jpg -> media ID 123
[INFO] Final post status: draft
[INFO] Dry run complete. No post created.
```

失败示例：

```text
[ERROR] WordPress API returned 403 Forbidden
[ERROR] Current user does not have permission to publish posts.
[HINT] Use an Author, Editor, or Administrator account.
```

---

## 不要做的事

不要实现以下内容，除非明确要求：

1. 不要做图形界面。
2. 不要接入浏览器自动化。
3. 不要用 Selenium 登录后台发布文章。
4. 不要使用 XML-RPC。
5. 不要默认批量发布。
6. 不要把 API 密码写进示例代码。
7. 不要生成复杂数据库。
8. 不要依赖 WordPress 后台页面结构。

---

## 最终交付内容

完成后应提供：

1. 可运行代码。
2. `.env.example`
3. `requirements.txt`
4. `README.md`
5. 示例文章 `articles/example.md`
6. 清晰的使用命令。
7. 常见错误排查说明。

## Markdown 转 HTML 要求

本项目的文章源文件使用 Markdown，但 WordPress REST API 发布文章时，`content` 字段应提交 HTML 内容，而不是原始 Markdown。

转换流程：

```text
Markdown 文件
  ↓
解析 Front Matter
  ↓
提取正文 Markdown
  ↓
转换为 HTML
  ↓
处理图片、代码块、标题、表格等内容
  ↓
提交到 WordPress REST API 的 content 字段
```

### 转换规则

必须将 Markdown 正文转换为 HTML 后再发布。

示例 Markdown：

````markdown
## Nginx 配置说明

这是正文内容。

```bash
systemctl status nginx
````

![封面图](../assets/nginx.jpg)

````

转换后的 HTML 应类似：

```html
<h2>Nginx 配置说明</h2>
<p>这是正文内容。</p>
<pre><code class="language-bash">systemctl status nginx</code></pre>
<p><img src="https://example.com/wp-content/uploads/2026/06/nginx.jpg" alt="封面图"></p>
````

### 推荐 Python 依赖

优先使用：

```text
markdown
PyYAML
beautifulsoup4
```

`requirements.txt` 示例：

```text
requests
python-dotenv
PyYAML
markdown
beautifulsoup4
```

### Markdown 扩展要求

Markdown 转 HTML 时建议启用以下扩展：

```python
extensions=[
    "extra",
    "tables",
    "fenced_code",
    "codehilite",
    "toc",
    "sane_lists"
]
```

至少需要支持：

1. 标题
2. 段落
3. 加粗
4. 列表
5. 表格
6. 代码块
7. 引用
8. 链接
9. 图片

### 图片处理要求

Markdown 中可能包含本地图片，例如：

```markdown
![架构图](../assets/arch.png)
```

发布到 WordPress 前不能直接保留本地路径。

必须执行以下逻辑：

1. 扫描 Markdown 或 HTML 中的本地图片路径。
2. 判断图片文件是否存在。
3. 上传图片到 `/wp-json/wp/v2/media`。
4. 获取 WordPress 返回的媒体 URL。
5. 将 HTML 中的本地图片路径替换为 WordPress 媒体库 URL。
6. 如果文章 Front Matter 中设置了 `cover`，则将该图片 ID 设置为 `featured_media`。

示例：

```markdown
![架构图](../assets/arch.png)
```

应替换为：

```html
<img src="https://example.com/wp-content/uploads/2026/06/arch.png" alt="架构图">
```

### 代码块处理要求

Markdown 中的代码块需要转换为 HTML：

````markdown
```bash
nginx -t
systemctl reload nginx
````

````

转换后应保留语言信息：

```html
<pre><code class="language-bash">nginx -t
systemctl reload nginx</code></pre>
````

不要丢失代码块缩进、换行和特殊字符。

### 表格处理要求

Markdown 表格需要转换为 HTML 表格。

示例：

```markdown
| 项目 | 说明 |
|---|---|
| Nginx | Web 服务 |
| PHP-FPM | PHP 运行服务 |
```

转换为：

```html
<table>
<thead>
<tr>
<th>项目</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td>Nginx</td>
<td>Web 服务</td>
</tr>
<tr>
<td>PHP-FPM</td>
<td>PHP 运行服务</td>
</tr>
</tbody>
</table>
```

### Gutenberg 兼容说明

WordPress 块编辑器 Gutenberg 底层也使用 HTML 存储内容，并且可以接受普通 HTML。

第一阶段不要求生成 Gutenberg 专用块注释，例如：

```html
<!-- wp:paragraph -->
<p>正文</p>
<!-- /wp:paragraph -->
```

第一阶段只需要生成干净、标准的 HTML，并通过 REST API 提交到 `content` 字段。

如果后续需要更好的块编辑器兼容性，可以在第二阶段增加 Markdown 到 Gutenberg Blocks 的转换能力。

### 内容清理要求

转换后的 HTML 应避免：

1. 多余的 `<html>`、`<body>`、`<head>` 标签。
2. 本地图片路径。
3. 空的段落标签。
4. 未闭合 HTML 标签。
5. 破坏代码块格式。
6. 把 Markdown 原文直接提交到 WordPress。

### dry-run 输出要求

`--dry-run` 模式下必须输出转换后的 HTML 内容摘要。

至少输出：

```text
[INFO] Markdown converted to HTML
[INFO] HTML length: 3862 chars
[INFO] Local images found: 2
[INFO] Images uploaded: 2
[INFO] Final content ready for WordPress
```

可以将完整 HTML 输出到临时文件：

```text
logs/preview.html
```

便于本地浏览器预览。
