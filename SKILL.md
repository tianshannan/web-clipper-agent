---
name: web-clipper-agent
description: |
  将微信公众号文章剪藏到 Obsidian Vault，支持单篇和批量剪藏、自动分类、图片本地化、P.A.I.R v5 标签体系。
  触发条件：用户要求"剪藏""保存文章到Obsidian""批量保存公众号文章""从IMA知识库剪藏到Vault"等。
  支持从 URL 直接抓取、从 JSON 列表批量处理、扫描 Vault 去重、更新 MOC 导航页。
---

# Web Clipper Agent

微信公众号文章剪藏到 Obsidian Vault 的自动化工具。

## 依赖

```bash
pip install requests beautifulsoup4 lxml markdownify
```

## Vault 路径

自动检测 Obsidian 配置（`%APPDATA%\Obsidian\obsidian.json`）。小虎的 Vault 路径：`D:\BaiduSyncdisk\陈小虎同学`。

可通过 `--vault` 或 `WebClipper(vault_path=...)` 覆盖。

## 快速使用

### 单篇剪藏

```bash
python scripts/clip.py --url "https://mp.weixin.qq.com/s/xxx" --category "知情同意" --account "公众号名"
```

### 批量剪藏（从 JSON 文件）

JSON 格式：`[{"url": "...", "title": "...", "category": "...", "folder": "..."}, ...]`

```bash
python scripts/clip.py --batch articles.json --output results.json
```

### 扫描 Vault 去重

```bash
python scripts/clip.py --scan-vault --output existing_urls.json
```

### 自定义 Vault 路径

```bash
python scripts/clip.py --url "..." --category "..." --vault "D:\MyVault" --base-dir "2-Projects/我的文章"
```

## 模块 API

```python
import sys
sys.path.insert(0, "scripts")
from clip import WebClipper

# 初始化
clipper = WebClipper(
    vault_path=r"D:\BaiduSyncdisk\陈小虎同学",
    base_dir="2-Projects/CRA学习文章",
)

# 单篇
result = clipper.clip_url(url, title="标题", category="知情同意", account="公众号名")

# 批量（自动去重）
results = clipper.clip_batch(articles_list, dedup=True)

# 扫描已有URL
urls = clipper.scan_vault_urls()

# 更新MOC
WebClipper.update_moc(vault_path, base_dir="2-Projects/CRA学习文章")

# 筛选和分类（用于从IMA知识库精选文章）
selected = WebClipper.filter_and_classify(all_articles, top_n=15)
```

## 输出格式

每篇文章保存为 P.A.I.R v5 格式的 Markdown 文件：

```yaml
---
title: 文章标题
source: https://mp.weixin.qq.com/s/xxx
author: 作者
account: 公众号名
publish_date: 2024-01-01
date_saved: 2026-08-08 15:42
content_type: 公众号文章
tags:
  - 状态/待消化
  - A/临床试验监查/知情同意
---

## 摘要
文章摘要（og:description 或正文首段）

## 正文
Markdown 正文内容（含本地图片链接 attachments/img-hash.jpg）

---
**来源**：[标题](URL)
**公众号**：公众号名
**剪藏时间**：2026-08-08 15:42
```

## 标签体系

默认使用 P.A.I.R v5 标签：
- `状态/待消化`：所有新剪藏文章
- `A/临床试验监查/{category}`：CRA 分类标签
- `A/个人成长`：CRA职业发展类

自定义标签映射：

```python
clipper = WebClipper(
    tag_map={
        "default": "A/我的领域/{category}",
        "其他分类": "A/其他标签",
    }
)
```

## 微信解析细节

微信公众号文章的 HTML 有多种特殊处理需求（data-src 图片、bold 内 br 撕裂、#标签清理等）。详见 [references/wechat-parsing.md](references/wechat-parsing.md)。

## 已知限制

- 微信视频文章只能提取文本，视频无法保存
- 需登录/付费/被删除的文章无法抓取
- 小程序卡片、投票组件无法保存
- 字体/字号/颜色/居中等装饰性排版不保留
- 图片 URL 可能过期失效（微信临时链接带 Expires 参数）
