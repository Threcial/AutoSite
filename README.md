# AutoSite - Markdown 上传工具

Windows 本地 Markdown 文件右键上传到 WordPress。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `config.example.yaml` 为 `config.yaml`，填写 WordPress 站点信息：

```yaml
site:
  base_url: "https://threcial.cn"
  username: "api_writer"
  application_password: "xxxx xxxx xxxx xxxx xxxx xxxx"
```

## 测试连接

```bash
python -m autosite check
```

## 安装右键菜单

```bash
python -m autosite install-context-menu
```

安装后右键 `.md` 文件 → `上传到 threcial.cn`。

## 卸载右键菜单

```bash
python -m autosite uninstall-context-menu
```

## 上传 Markdown

```bash
python -m autosite upload "D:\articles\test.md"
```

### 预览模式（不真正上传）

```bash
python -m autosite upload "D:\articles\test.md" --dry-run
```

## Front Matter 示例

```yaml
---
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
---
```

## 常见错误

| 错误 | 原因 |
|------|------|
| 401 | Application Password 错误 |
| 403 | 当前用户没有创建/编辑文章权限 |
| 分类创建失败 | 分类不存在且 `auto_create_categories: false` |
| 标签创建失败 | 标签不存在且 `auto_create_tags: false` |
| 图片上传失败 | 本地图片路径错误或 WordPress 媒体库异常 |
