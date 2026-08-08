# Web Clipper Agent

将微信公众号文章自动剪藏到 Obsidian Vault 的工具，支持单篇/批量剪藏、自动分类、图片本地化、P.A.I.R v5 标签体系。

## 功能

- **单篇剪藏**：从微信文章 URL 抓取内容，转为 Markdown 保存到 Obsidian
- **批量剪藏**：从 JSON 列表批量处理，自动 URL+标题双去重
- **自动分类**：18 个 CRA 领域关键词匹配 + 质量评分筛选
- **图片本地化**：微信 data-src 图片提取、hash 去重下载到 attachments/
- **标签体系**：P.A.I.R v5 格式，`状态/待消化` + `A/临床试验监查/{子领域}`
- **MOC 导航**：自动生成 Obsidian MOC 索引页

## 安装

```bash
pip install requests beautifulsoup4 lxml markdownify
```

## 使用

### 单篇剪藏

```bash
python scripts/clip.py --url "https://mp.weixin.qq.com/s/xxx" --category "知情同意" --account "公众号名"
```

### 批量剪藏

```bash
python scripts/clip.py --batch articles.json --output results.json
```

### 扫描 Vault 去重

```bash
python scripts/clip.py --scan-vault --output existing_urls.json
```

### Python 模块调用

```python
import sys
sys.path.insert(0, "scripts")
from clip import WebClipper

clipper = WebClipper(vault_path="D:\\MyVault")
result = clipper.clip_url(url, title="标题", category="知情同意", account="公众号名")
results = clipper.clip_batch(articles_list, dedup=True)
```

## 输出格式

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
文章摘要

## 正文
Markdown 正文（含本地图片链接 attachments/img-hash.jpg）

---
**来源**：[标题](URL)
**公众号**：公众号名
**剪藏时间**：2026-08-08 15:42
```

## 微信公众号特殊处理

- `data-src` → `src` 图片属性修复
- 粗体 `<br>` 撕裂修复
- 微信 `#话题标签` 清理（不污染 Obsidian 标签体系）
- 失效页面检测（已删除/私密/迁移）
- `display:none` 隐藏元素过滤
- HTML 数字实体解码
- `\x0d\x0a` 转义字符清理
- 摘要回退（无 og:description 时取正文首段）

详见 [references/wechat-parsing.md](references/wechat-parsing.md)

## 已知限制

- 微信视频文章只能提取文本
- 需登录/付费/被删除的文章无法抓取
- 小程序卡片、投票组件无法保存
- 装饰性排版（字体/字号/颜色/居中）不保留

## License

MIT
