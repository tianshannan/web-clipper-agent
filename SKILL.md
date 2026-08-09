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

自动检测 Obsidian 配置（`%APPDATA%\Obsidian\obsidian.json`，优先 open=True 的 vault）。小虎的 Vault 路径：`D:\BaiduSyncdisk\陈小虎同学`。

可通过 `--vault` 或 `WebClipper(vault_path=...)` 覆盖。

## 快速使用

### 单篇剪藏

```bash
python scripts/clip.py --url "https://mp.weixin.qq.com/s/xxx" --category "知情同意" --account "公众号名"
```

### 批量剪藏（从 JSON 文件）

JSON 格式：`[{"url": "...", "title": "...", "category": "...", "folder": "..."}, ...]`

```bash
# 默认间隔1秒，避免触发频率限制
python scripts/clip.py --batch articles.json --output results.json

# 自定义请求间隔（秒），大批量时建议 --rate 2
python scripts/clip.py --batch articles.json --output results.json --rate 2
```

### 扫描 Vault 去重

```bash
# 扫描后输出到JSON文件，用于后续去重
python scripts/clip.py --scan-vault --output existing_urls.json

# 扫描结果格式：{"urls": ["url1", ...], "titles": ["title1", ...]}
# 注意：若扫描结果异常（如仅发现少量URL），请手动确认 --vault 参数是否正确
```

### 更新 MOC 导航页

```bash
# 重新扫描 Vault 中所有文章，生成最新 MOC 索引
python scripts/clip.py --update-moc --vault "D:\BaiduSyncdisk\陈小虎同学" --base-dir "2-Projects/CRA学习文章"
```

### 自定义 Vault 路径和输出目录

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

# 单篇剪藏
result = clipper.clip_url(url, title="标题", category="知情同意", account="公众号名")

# 批量剪藏（自动去重）
results = clipper.clip_batch(articles_list, dedup=True)

# 扫描已有URL（返回 {"urls": set, "titles": set, "total_files": int}）
urls = clipper.scan_vault_urls()

# 更新MOC导航页
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

## IMA 知识库集成工作流

从 IMA 知识库批量获取文章 URL 并剪藏的完整流程：

```python
import subprocess, json, time

# 1. 通过 IMA API 获取文章微信原始 URL
payload = json.dumps({"media_id": media_id})
auth = json.dumps({"clientId": CLIENT_ID, "apiKey": API_KEY})
result = subprocess.run(
    ["node", "ima_api.cjs", "openapi/wiki/v1/get_media_info", payload, auth],
    capture_output=True, encoding="utf-8",  # Windows 必须加 encoding='utf-8'
    timeout=30
)
data = json.loads(result.stdout)
url = data["data"]["url_info"]["url"]

# 2. 间隔 2 秒避免 API 频率限制
time.sleep(2)

# 3. 收集所有 URL 后，写入 batch JSON 文件
batch = [{"url": url, "title": title, "category": category, "folder": folder}]
with open("batch_clip.json", "w") as f:
    json.dump(batch, f, ensure_ascii=False, indent=2)

# 4. 用 clip.py 批量剪藏
# python scripts/clip.py --batch batch_clip.json --output results.json --rate 2
```

**Windows 注意事项：**
- 调用 `subprocess.run` 时**必须加 `encoding="utf-8"`**，否则 Windows 默认 GBK 解码会报错
- IMA API `get_media_info` 有每日调用上限（约 150 次），超出后返回 `"资料获取次数已达上限"`，需隔天继续
- 批量处理时建议先扫描 Vault 去重，再将新文章分批获取 URL

## 微信解析细节

微信公众号文章的 HTML 有多种特殊处理需求（data-src 图片、bold 内 br 撕裂、#标签清理等）。详见 [references/wechat-parsing.md](references/wechat-parsing.md)。

## 已知限制

- 微信视频文章只能提取文本，视频无法保存
- 需登录/付费/被删除的文章无法抓取
- 小程序卡片、投票组件无法保存
- 字体/字号/颜色/居中等装饰性排版不保留
- 图片 URL 可能过期失效（微信临时链接带 Expires 参数）
- `--scan-vault` 默认扫描整个 Vault，若结果异常请检查 `--vault` 参数是否正确指向目标 Vault