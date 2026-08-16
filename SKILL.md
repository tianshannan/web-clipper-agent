---
name: web-clipper-agent
description: |
  自动化网页剪藏到 Obsidian Vault。v5.0：合并 v3.2（文本处理优势）+ v4.0（类架构 + 高级功能）。
  触发条件：用户说"剪藏""保存文章""收藏网页""存到Obsidian""clip这篇文章"。
  支持：requests 直接抓取 + browser 降级、失效页面检测、粗体/标题 br 修复、表格优先解析、
  图片 hash 去重本地化、16 步 Markdown 后处理、摘要回退、P.A.I.R v5 frontmatter、
  微信 #标签清理、扫描去重、CRA 自动分类、MOC 导航页、argparse CLI。
  支持微信公众号、知乎、博客等各类网页，支持批量剪藏。
---

# Web Clipper Agent v5.0

合并 v3.2（文本处理优势）+ v4.0（类架构 + 高级功能）的完整网页剪藏工具。

## ⚠️ 版本管理规则（重要）

### 每次使用前：检查 GitHub 版本

**在执行剪藏任务前，必须先检查 GitHub 上的版本是否比本地新：**

```python
# 1. 读取本地版本号
import sys, os
sys.path.insert(0, os.path.join(os.getenv("SKILL_PATH", ""), "web-clipper-agent", "scripts"))
import clip
print(f"本地版本: v{clip.VERSION}")

# 2. 获取 GitHub 版本号
import requests
resp = requests.get("https://raw.githubusercontent.com/tianshannan/web-clipper-agent/main/scripts/clip.py", timeout=10)
github_code = resp.text
# 提取 VERSION 字符串
import re
m = re.search(r'VERSION\s*=\s*"([\d.]+)"', github_code)
github_version = m.group(1) if m else "unknown"
print(f"GitHub 版本: v{github_version}")

# 3. 如果 GitHub 版本更新，提示用户
if github_version != clip.VERSION:
    print(f"⚠️ 版本不一致！本地 v{clip.VERSION}，GitHub v{github_version}")
    # 提示用户更新后再执行任务
```

**如果 GitHub 版本更新**：提示用户"GitHub 上有新版本 vX.X，建议更新本地版本后再执行剪藏任务"，等待用户确认后再继续。

### 每次 SKILL 更新后：提醒上传 GitHub

**当对这个技能的任何文件（SKILL.md / clip.py / references/）做了修改后，必须在回复末尾提醒用户：**

> ⚠️ web-clipper-agent 技能已更新（vX.X），请记得将更改推送到 GitHub：
> ```bash
> cd <技能目录>
> git add -A && git commit -m "update to vX.X" && git push
> ```

## 版本演进

| 特性 | v3 | v3.1 | v3.2 | v4.0 | v5.0（当前） |
|------|----|------|------|------|-------------|
| 抓取方式 | requests | requests+重试 | requests+browser降级 | requests | requests+browser降级 |
| 失效页面检测 | 无 | 无 | ✅ | ✅ | ✅ |
| 粗体/标题 br 修复 | 无 | 无 | ✅ | ✅ | ✅ |
| 表格优先解析 | 无 | 无 | ✅ | ✅ | ✅ |
| 图片 hash 去重 | 无 | ✅ | ✅ | ✅ | ✅ |
| 图片占位符系统 | 无 | 无 | ✅ | 无 | ✅ |
| 相对链接补全 | 无 | ✅ | ✅ | 无 | ✅ |
| 摘要回退 | 无 | 无 | ✅ | 无 | ✅ |
| 时间精确到分钟 | 无 | 无 | ✅ | 无 | ✅ |
| 16步Markdown后处理 | 无 | 无 | ✅ | 无 | ✅ |
| 文件名Unicode清理 | 无 | 无 | ✅ | 无 | ✅ |
| WebClipper 类 | 无 | 无 | 无 | ✅ | ✅ |
| 扫描去重 | 无 | 无 | 无 | ✅ | ✅ |
| CRA自动分类 | 无 | 无 | 无 | ✅ | ✅ |
| MOC导航页 | 无 | 无 | 无 | ✅ | ✅ |
| 质量评分筛选 | 无 | 无 | 无 | ✅ | ✅ |
| argparse CLI | 无 | 无 | 无 | ✅ | ✅ |
| browser降级fallback | 无 | 有 | ✅ | 无 | ✅ |
| 通用网页支持 | 无 | 无 | ✅ | 无 | ✅ |
| GitHub版本检查 | 无 | 无 | 无 | 无 | ✅ |

## Vault 信息

- **路径**：`E:\OneDrive\陈小虎同学`（自动检测 obsidian.json，fallback 到此路径）
- **默认入口**：`1-Inbox`（无分类时）
- **分类输出**：`2-Projects/CRA学习文章/{category}/`（指定 --category + --base-dir 时）
- **图片目录**：`attachments`（Vault 根目录下，跨文章共享去重）
- **标签体系**：P.A.I.R v5（状态/待消化 + A/领域 + 卡片/类型）

## 输出格式

### Frontmatter

```yaml
---
title: 文章标题
source: https://mp.weixin.qq.com/s/xxxx
author: 署名作者
account: 公众号名称
publish_date: 2025-10-05 06:00
date_saved: 2026-08-16 12:00
content_type: 公众号文章
tags:
  - 状态/待消化
  - A/临床试验监查/知情同意    # 有分类时才有
---
```

### 正文结构

```markdown
## 摘要

（官方 og:description，或正文首段回退，或"（无摘要）"）

## 正文

（Markdown 正文，图片引用为 `![[attachments/img-hash.jpg]]`）

---

**来源**：[文章标题](URL)
**作者**：作者
**公众号**：公众号名
**发布日期**：2025-10-05 06:00
**剪藏时间**：2026-08-16 12:00
```

## 工作流

### 1. 获取 URL

URL 来源（按优先级）：
- **用户直接提供**：用户给出网页链接
- **本地 Excel 数据源**（推荐）：读取 `E:\OneDrive\公众号\公众号链接\` 下的 31 个 Excel 文件。配套 `E:\OneDrive\公众号\公众号广告清理\IMA知识库清理清单.xlsx` 排除 9418 篇垃圾文章
- **IMA 知识库搜索**（备选）：使用 ima-skill 搜索 → `get_media_info` 获取真实 URL（有每日 ~150 次限制）
- **批量剪藏**：用户提供多个 URL 或指定 IMA 知识库文件夹

### 2. 执行剪藏

```python
import sys, os
sys.path.insert(0, os.path.join(os.getenv("SKILL_PATH", ""), "web-clipper-agent", "scripts"))
import clip

# 方式一：v3.2 兼容 API（写入 1-Inbox）
result = clip.clip_url(url, download_imgs=True)

# 方式二：WebClipper 类 API（支持分类写入）
from clip import WebClipper
clipper = WebClipper(
    vault_path=r"E:\OneDrive\陈小虎同学",
    base_dir="2-Projects/CRA学习文章",  # None = 1-Inbox 模式
)

# 单篇（无分类 → 1-Inbox）
result = clipper.clip_url(url, download_imgs=True)

# 单篇（有分类 → 2-Projects/CRA学习文章/知情同意/）
result = clipper.clip_url(url, category="知情同意", account="公众号名")

# 批量（自动去重）
results = clipper.clip_batch(articles_list, dedup=True)

# 扫描已有 URL
urls = clipper.scan_vault_urls()

# 更新 MOC 导航页
WebClipper.update_moc(vault_path, base_dir="2-Projects/CRA学习文章")

# 筛选和分类
selected = WebClipper.filter_and_classify(all_articles, top_n=15)
```

### 3. 内部处理流程（11 步）

#### Step 0: 失效页面检测
- 抓取 HTML 后立即检测：内容被删除、违规无法查看、触发验证页、账号注销/迁移
- 命中任一模式 → 返回 `{"success": false, "error": "页面已失效..."}`，不产出垃圾文件

#### Step 1: 抓取 HTML
- **首选**：`requests.Session()` 复用连接池 + UA 伪装 + 微信 Referer 防盗链
- **重试**：失败自动重试 3 次，间隔递增（2s/4s/6s）
- **降级**：requests 失败时切换到 browser headless

#### Step 2: 提取元信息
- 微信：`og:title` / `#activity-name`、`meta author` / `#js_author_name`、`#js_name`、`var ct` 时间戳 → 精确到分钟、`og:description`
- 通用：`og:title` / `<h1>` / `<title>`、`meta author`、`og:description` / `meta description`

#### Step 2.5: 元信息转义清理 + 无关元素移除 + 相对链接补全
- title/author/account/description 中的 `\x0d\x0a` 转义字符 → 空格
- HTML 数字实体解码（`&#NN;` / `&#xNN;` / 命名实体）
- 移除 script/style/nav/footer/iframe + 微信广告/推荐/二维码 class
- 移除 `display:none` 隐藏元素（不移除 `visibility:hidden`）
- 相对链接补全为绝对 URL

#### Step 2.6: 粗体/斜体内部 `<br>` 合并 + 标题内 `<br>` 压缩
- `<strong>/<b>/<em>/<i>` 内部的 `<br>` → 空格，防止 `**` 标记被撕开
- `<h1-6>` 内的 `<br>` → 空格，防止非法多行标题

#### Step 2.7: data-src → src（微信懒加载修复）

#### Step 3: 表格优先解析
- markdownify 之前，BeautifulSoup 先解析 `<table>` → Markdown 表格
- 单元格内 `<br>` 转空格，保证一行一格不拆行

#### Step 4: 图片处理（占位符 + hash 去重 + 防盗链）
- 提取 `data-src`（微信懒加载）和 `src`（通用）
- 占位符替换 `<img>` 标签（Unicode 私用区字符）
- **hash 命名**：`img-{URL的MD5前12位}.{ext}`，跨文章去重（全局缓存）
- **防盗链**：微信图片带 `Referer: https://mp.weixin.qq.com/`
- **路径前缀**：`![[attachments/img-hash.jpg]]`
- 下载失败 → `<!-- 图片下载失败 #N -->`

#### Step 5: HTML → Markdown（16 步后处理）
1. `***text***` → `**text**`
2. 行尾 `***` 清理
3. 行内 `###` → `**text**`
4. 未闭合 `**` 补全
5. 空粗体 `****` 清理
6. `\x0d\x0a` 转义字符清理
7. HTML 数字实体解码
8. 空链接清除
9. 行尾空格清理
10. 列表项误转标题修复
11. 空标题标记清理
12. 装饰性标题清理
13. 孤立粗体标记行清理
14. 行尾空粗体对清理
15. 粗体标记周围空格修复
16. 多余空行压缩

#### Step 6: 微信 #标签清理
- 删除整行 `#话题标签` 和行内嵌入的 `#标签`
- 不处理 frontmatter 中的 tags

#### Step 7: P.A.I.R 格式化（含摘要回退）→ 写入 Vault
- frontmatter：title/source/author/account/publish_date/date_saved/content_type/tags
- **摘要回退**：无 `og:description` 时取正文首个有效段落（≥20字），跳过推广段/纯图片/纯链接
- 有 category + base_dir → 写入 `{base_dir}/{category}/`，加分类标签
- 无 category → 写入 `1-Inbox/`，只加 `状态/待消化`

### 4. 返回值

```python
{
    "success": True,
    "file_path": "E:\\OneDrive\\陈小虎同学\\1-Inbox\\文章标题.md",
    "title": "文章标题",
    "author": "作者",
    "account": "公众号名",
    "publish_date": "2025-10-05 06:00",
    "content_type": "公众号文章",
    "content_length": 1459,
    "image_total": 2,
    "image_downloaded": 2,
    "image_failed": 0,
    "fetch_method": "requests"
}
```

## 命令行用法

```bash
# 单篇（写入 1-Inbox）
python scripts/clip.py --url "https://mp.weixin.qq.com/s/xxxx"

# 单篇 + 分类（写入 2-Projects/CRA学习文章/知情同意/）
python scripts/clip.py --url "..." --category "知情同意" --account "公众号名" --base-dir "2-Projects/CRA学习文章"

# 批量（JSON 文件）
python scripts/clip.py --batch articles.json --output results.json --rate 2

# 批量（URL 列表文件，v3.2 兼容）
python scripts/clip.py -f urls.txt

# 扫描 Vault 去重
python scripts/clip.py --scan-vault --output existing_urls.json

# 更新 MOC 导航页
python scripts/clip.py --update-moc --base-dir "2-Projects/CRA学习文章"

# 查看版本
python scripts/clip.py --version

# 自定义 Vault
python scripts/clip.py --url "..." --vault "D:\MyVault" --base-dir "2-Projects/我的文章"
```

## 分类写入（CRA学习文章）

剪藏完成后，可按 CRA 分类移动到 `2-Projects/CRA学习文章/{分类}/` 目录：
- 18 个 CRA 分类（知情同意/安全性报告/方案违背/伦理审查/遗传办/药物管理/生物样本/数据管理/研究者资质/质量保证/受试者管理/文档管理/机构管理/监查访视/方案设计审核/项目管理/法规解读/CRA职业发展）
- 移动后更新 frontmatter tags：`A/临床试验监查/{子领域}` 或 `A/个人成长`
- MOC 导航页：`2-Projects/CRA学习文章/MOC-CRA学习文章.md`

## IMA 知识库集成

从 IMA 知识库批量获取文章 URL 并剪藏的流程：

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

# 3. 批量剪藏
articles = [{"url": url, "title": title, "category": category, "account": folder}]
clipper.clip_batch(articles, dedup=True)
```

详见 [references/ima-knowledge-base.md](references/ima-knowledge-base.md)。

## 微信解析细节

微信公众号文章的 HTML 有多种特殊处理需求。详见 [references/wechat-parsing.md](references/wechat-parsing.md)。

## 已知限制

1. 需登录/付费/被删除的文章无法抓取（requests 无登录态）
2. 嵌入视频只留链接，无法保存视频内容
3. 小程序卡片、投票组件无法保存
4. 字体/字号/颜色/居中等装饰性排版不保留（Markdown 格式天然限制）
5. 重度 JS 渲染的 SPA 页面可能提取失败（requests 不执行 JS），browser 降级可覆盖部分
6. IMA API 批量调用有频率限制（约 50 次后触发，需间隔 1.5-2 秒）
7. 大页面（3MB+）偶发 requests 返回不完整 HTML，重试可解决

## 格式保真边界

**完整保留**：标题层级、段落、粗体/斜体、列表、引用、超链接、表格、图片位置与内容。

**丢失**（Markdown 天然限制）：字体/字号/颜色、居中、背景色等纯视觉样式；嵌入视频只留链接；小程序卡片、投票组件无法保存。
