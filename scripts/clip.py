#!/usr/bin/env python3
"""
web-clipper-agent v4.0 — 微信公众号文章剪藏到 Obsidian Vault

Usage:
  # 单篇剪藏
  python clip.py --url "https://mp.weixin.qq.com/s/xxx" --category "知情同意" --account "公众号名"

  # 批量剪藏（从 JSON 文件）
  python clip.py --batch articles.json

  # 扫描 Vault 已有 URL（用于去重）
  python clip.py --scan-vault /path/to/vault

  # 自定义 Vault 路径和输出目录
  python clip.py --url "..." --category "..." --account "..." --vault "D:\\MyVault" --base-dir "2-Projects/CRA学习文章"

Module API:
  from clip import WebClipper
  clipper = WebClipper(vault_path="D:\\MyVault", base_dir="2-Projects/CRA学习文章")
  result = clipper.clip_url(url, title="...", category="知情同意", account="公众号名")
  results = clipper.clip_batch(articles_list, dedup=True)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, NavigableString
import markdownify


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

WECHAT_REFERER = "https://mp.weixin.qq.com/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

INVALID_PAGE_KEYWORDS = [
    "已被发布者删除", "违规无法查看", "当前环境异常",
    "完成验证后即可继续访问", "公众号已迁移", "账号已注销",
    "环境异常", "访问过于频繁",
]

# Tag mapping: category name → Obsidian tag path
# Override via WebClipper(tag_map={...}) if needed
DEFAULT_TAG_MAP = {
    # CRA categories → A/临床试验监查/{子领域}
    "default": "A/临床试验监查/{category}",
    # Override for specific categories
    "CRA职业发展": "A/个人成长",
}

# Quality scoring keywords for article selection
QUALITY_POSITIVE = [
    "分享", "干货", "如何", "详解", "清单", "SOP", "要点", "实操", "案例",
    "总结", "指南", "流程", "模板", "工具", "方法", "实践", "经验", "技巧",
    "规范", "标准", "检查", "核查", "对比", "分析", "解析", "深度", "全面",
    "完整", "step", "步骤", "常见问题", "FAQ", "避坑", "陷阱", "误区",
]
QUALITY_NEGATIVE = [
    "大变天", "扎心", "焦虑", "震惊", "爆款", "10万+",
    "阅读量", "粉丝", "转发", "点赞", "投票", "征集",
]

# Exclude patterns for non-learning content
EXCLUDE_PATTERNS = [
    "招聘", "招人", "诚聘", "岗位", "求职", "简历", "面试",
    "培训通知", "会议通知", "会议日程", "大会", "峰会", "论坛通知",
    "广告", "推广", "优惠", "活动", "抽奖", "福利",
    "患者招募", "受试者招募", "入组通知",
    "节日", "新年", "中秋", "国庆", "春节", "元旦", "端午",
    "开工大吉", "放假", "休息", "温馨提示", "关注公众号", "扫码", "二维码",
]

# CRA category keywords for auto-classification
CRA_CATEGORIES = {
    "知情同意": ["知情同意", "知情", "ICF", "informed consent", "同意书"],
    "安全性报告": ["安全性", "SAE", "AESI", "不良事件", "SUSAR", "安全性报告", "药物警戒", "PV", "个例安全", "安全报告"],
    "方案违背": ["方案违背", "方案偏离", "deviation", "violation", "PD", "违背", "合规"],
    "伦理审查": ["伦理", "IRB", "EC", "伦理审查", "伦理委员会"],
    "遗传办": ["遗传办", "人类遗传资源", "HGR", "遗传资源"],
    "药物管理": ["药物管理", "IMP", "试验药物", "试验用药品", "drug management", "药物计数", "药物发放", "储运", "冷链", "药房"],
    "生物样本": ["生物样本", "样本管理", "central lab", "样本采集", "样本处理", "生物标志物", "biomarker", "PK采样", "PK样本"],
    "数据管理": ["数据管理", "EDC", "data management", "数据录入", "数据核查", "数据质量", "query", "质疑", "CRF", "eCRF", "数据标准", "CDISC", "SDTM"],
    "研究者资质": ["研究者", "PI", "sub-I", "CRC资质", "研究者资质", "授权", "研究者档案", "CV", "financial disclosure"],
    "质量保证": ["质量保证", "QA", "QC", "稽查", "audit", "inspection", "视察", "质量体系", "质量风险管理", "QMS", "CAPA", "纠正预防"],
    "受试者管理": ["受试者", "subject", "受试者管理", "受试者依从性", "入组", "筛选", "脱落", "退出", "受试者保护"],
    "文档管理": ["文档管理", "ISF", "研究者文件夹", "TMF", "trial master file", "文档归档", "归档", "文档体系", "文件管理"],
    "机构管理": ["机构", "site management", "机构管理", "SMO", "CRC管理", "中心管理", "site selection", "中心筛选", "中心启动", "PSV", "SSV", "SIV", "SMV", "RMV", "COV", "close-out"],
    "监查访视": ["监查", "monitoring", "监查计划", "监查报告", "监查访视", "MVF", "monitoring visit", "现场监查", "监查频率", "RBM", "基于风险的监查", "中心化监查", "risk-based"],
    "方案设计审核": ["方案设计", "protocol design", "方案审核", "protocol review", "入排标准", "inclusion", "exclusion", "终点", "endpoint", "盲法", "randomization", "随机化"],
    "项目管理": ["项目管理", "PM", "project management", "项目计划", "进度管理", "budget", "预算", "里程碑", "project plan", "CRO管理", "供应商管理"],
    "法规解读": ["法规", "GCP", "ICH", "指导原则", "guideline", "regulation", "NMPA", "CDE", "FDA", "EMA", "法规解读", "药政", "注册", "药品注册", "临床试验管理办法"],
    "CRA职业发展": ["CRA", "CRC", "职业发展", "职业规划", "晋升", "技能提升", "面试", "转岗", "薪资", "职场", "communication", "沟通技巧", "时间管理", "工作效率"],
}


# ──────────────────────────────────────────────
# WebClipper class
# ──────────────────────────────────────────────

class WebClipper:
    """Core clipping engine — fetch, parse, convert, save."""

    def __init__(self, vault_path=None, base_dir="2-Projects/CRA学习文章",
                 tag_map=None, download_images=True, rate_limit=1.0):
        """
        Args:
            vault_path: Obsidian Vault root path. If None, auto-detect from obsidian.json
            base_dir: Subdirectory within Vault for clipped articles
            tag_map: Override default category→tag mapping
            download_images: Whether to download images locally
            rate_limit: Seconds between requests
        """
        self.vault_path = vault_path or self._detect_vault_path()
        self.base_dir = base_dir
        self.output_base = os.path.join(self.vault_path, base_dir)
        self.tag_map = tag_map or DEFAULT_TAG_MAP
        self.download_images_flag = download_images
        self.rate_limit = rate_limit
        self._existing_urls = None  # lazy-loaded dedup set

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    @staticmethod
    def _detect_vault_path():
        """Auto-detect Vault path from Obsidian config. Prefer open=True vault."""
        config_path = os.path.expandvars(r"%APPDATA%\Obsidian\obsidian.json")
        if os.path.exists(config_path):
            import json as _json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = _json.load(f)
            vaults = config.get("vaults", {})
            # Prefer open=True vault
            for vid, vinfo in vaults.items():
                if vinfo.get("open") and vinfo.get("path") and os.path.exists(vinfo["path"]):
                    return vinfo["path"]
            # Fallback to first existing vault
            for vid, vinfo in vaults.items():
                path = vinfo.get("path", "")
                if path and os.path.exists(path):
                    return path
        # Fallback: common paths (BaiduSyncdisk preferred)
        for p in [r"D:\BaiduSyncdisk\陈小虎同学", r"C:\Users\陈虎\Nutstore\1\陈小虎同学"]:
            if os.path.exists(p):
                return p
        raise RuntimeError("Cannot detect Obsidian Vault path. Please specify --vault.")

    # ─── Public API ───

    def clip_url(self, url, title=None, category="其他", account=""):
        """
        Clip a single URL to Obsidian Vault.

        Returns:
            dict: {"success": bool, "file_path": str, "title": str, "error": str}
        """
        html = self._fetch_html(url)
        if not html:
            return {"success": False, "error": "Failed to fetch HTML", "title": title or ""}

        valid, reason = self._check_page_valid(html)
        if not valid:
            return {"success": False, "error": f"Invalid page: {reason}", "title": title or ""}

        result, error = self._html_to_markdown(html)
        if error:
            return {"success": False, "error": error, "title": title or ""}

        content_md = result["markdown"]
        meta = result["meta"]
        if not meta["title"]:
            meta["title"] = title or "Untitled"

        # Download and embed images
        if self.download_images_flag:
            img_urls = self._collect_images(html)
            if img_urls:
                img_dir = os.path.join(self.output_base, category, "attachments")
                img_map = self._download_images(img_urls, img_dir)
                content_md = self._replace_image_urls(content_md, img_map)

        # Remove any remaining empty image tags
        content_md = re.sub(r'!\[\]\(\)', '', content_md)
        content_md = re.sub(r'\n{3,}', '\n\n', content_md)

        note = self._build_note(
            title=meta["title"], url=url, author=meta.get("author", ""),
            account=account, publish_time=meta.get("publish_time", ""),
            description=meta.get("description", ""),
            content_md=content_md, category=category,
        )
        filepath = self._save_to_vault(meta["title"], note, category)

        return {"success": True, "file_path": filepath, "title": meta["title"], "error": ""}

    def clip_batch(self, articles, dedup=True, dedup_titles=True):
        """
        Batch clip multiple articles.

        Args:
            articles: list of dicts with keys: url, title, category, account/folder
            dedup: skip URLs already in Vault
            dedup_titles: skip titles already in Vault

        Returns:
            list of result dicts
        """
        results = []
        if dedup or dedup_titles:
            existing = self._load_existing_urls()
            existing_titles = self._load_existing_titles()
        else:
            existing, existing_titles = set(), set()

        for i, article in enumerate(articles):
            url = article.get("url", "")
            title = article.get("title", "")
            category = article.get("category") or article.get("primary_category", "其他")
            account = article.get("account") or article.get("folder", "")

            if not url:
                results.append({**article, "success": False, "error": "No URL"})
                continue

            if dedup and url in existing:
                print(f"  [{i+1}/{len(articles)}] SKIP (URL in Vault): {title[:40]}", flush=True)
                results.append({**article, "success": False, "error": "duplicate_url", "url": url})
                continue

            if dedup_titles and title in existing_titles:
                print(f"  [{i+1}/{len(articles)}] SKIP (title in Vault): {title[:40]}", flush=True)
                results.append({**article, "success": False, "error": "duplicate_title", "url": url})
                continue

            print(f"  [{i+1}/{len(articles)}] Clipping: {title[:50]}...", flush=True)
            result = self.clip_url(url, title=title, category=category, account=account)

            if result["success"]:
                existing.add(url)
                existing_titles.add(title)
                print(f"    -> OK: {result['file_path'][-60:]}", flush=True)
            else:
                print(f"    -> FAIL: {result['error']}", flush=True)

            results.append({**article, **result})
            time.sleep(self.rate_limit)

        return results

    def scan_vault_urls(self):
        """Scan Vault for existing source URLs and titles (for dedup)."""
        url_set = set()
        title_set = set()
        count = 0
        for root, dirs, files in os.walk(self.vault_path):
            if '.obsidian' in root or 'attachments' in root or '.trash' in root:
                continue
            for f in files:
                if not f.endswith('.md'):
                    continue
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
                        content = fh.read(4096)
                    m = re.search(r'^source:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        url = m.group(1).strip().strip('"').strip("'")
                        if url.startswith('http'):
                            url_set.add(url)
                    m2 = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
                    if m2:
                        title_set.add(m2.group(1).strip().strip('"').strip("'"))
                    count += 1
                except:
                    pass
        return {"urls": url_set, "titles": title_set, "total_files": count}

    # ─── Static utility methods ───

    @staticmethod
    def filter_and_classify(articles, top_n=15):
        """
        Filter articles for CRA learning value and classify into categories.

        Args:
            articles: list of dicts with 'title' key
            top_n: max articles per category

        Returns:
            list of dicts with added 'categories', 'score', 'primary_category' keys
        """
        # Cross-folder dedup by title
        seen = set()
        deduped = []
        for a in articles:
            title = a.get("title", "").strip()
            if not title or len(title) < 4 or title in seen:
                continue
            seen.add(title)
            deduped.append(a)

        # Exclude non-learning
        exclude_re = re.compile('|'.join(EXCLUDE_PATTERNS))

        # Filter and classify
        filtered = []
        for a in deduped:
            title = a["title"].strip()
            if exclude_re.search(title):
                continue
            t_lower = title.lower()
            matched = []
            for cat, keywords in CRA_CATEGORIES.items():
                for kw in keywords:
                    if kw.lower() in t_lower:
                        matched.append(cat)
                        break
            if matched:
                score = WebClipper._score_article(title)
                filtered.append({**a, "categories": matched, "score": score})

        # Select top N per category
        cat_articles = defaultdict(list)
        for a in filtered:
            for cat in a["categories"]:
                cat_articles[cat].append(a)

        selected = []
        seen_global = set()
        for cat in sorted(cat_articles.keys()):
            for a in sorted(cat_articles[cat], key=lambda x: -x["score"]):
                if a["title"] in seen_global:
                    continue
                seen_global.add(a["title"])
                a["primary_category"] = cat
                selected.append(a)
                if sum(1 for s in selected if s["primary_category"] == cat) >= top_n:
                    break

        return selected

    @staticmethod
    def _score_article(title):
        score = 0
        t_lower = title.lower()
        for kw in QUALITY_POSITIVE:
            if kw.lower() in t_lower:
                score += 2
        for kw in QUALITY_NEGATIVE:
            if kw.lower() in t_lower:
                score -= 3
        if len(title) > 15:
            score += 1
        if len(title) > 25:
            score += 1
        return score

    @staticmethod
    def update_moc(vault_path, base_dir="2-Projects/CRA学习文章", moc_name="MOC-CRA学习文章"):
        """Update MOC navigation page for all articles in base_dir."""
        cra_base = os.path.join(vault_path, base_dir)
        categories = defaultdict(list)
        for root, dirs, files in os.walk(cra_base):
            if 'attachments' in root or '.obsidian' in root:
                continue
            for f in files:
                if not f.endswith('.md') or f.startswith('MOC-'):
                    continue
                fpath = os.path.join(root, f)
                rel_dir = os.path.relpath(root, cra_base)
                if rel_dir == '.':
                    continue
                title = f.replace('.md', '')
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
                        content = fh.read(2048)
                    m = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
                    if m:
                        title = m.group(1).strip().strip('"').strip("'")
                except:
                    pass
                categories[rel_dir].append(title)

        total = sum(len(v) for v in categories.values())
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        moc = f"""---
title: CRA学习文章导航
date_updated: {now}
total_articles: {total}
total_categories: {len(categories)}
tags:
  - MOC/CRA学习
---

# CRA学习文章导航

> 共 **{total}** 篇文章，覆盖 **{len(categories)}** 个分类。
> 最后更新：{now}

"""
        for cat in sorted(categories.keys()):
            articles = sorted(categories[cat])
            moc += f"## {cat}（{len(articles)}篇）\n\n"
            for title in articles:
                filename = re.sub(r'[<>:"/\\|?*]', '-', title.strip())[:80]
                moc += f"- [[{filename}]]\n"
            moc += "\n"

        moc_path = os.path.join(cra_base, f"{moc_name}.md")
        with open(moc_path, 'w', encoding='utf-8') as f:
            f.write(moc)
        return moc_path

    # ─── Internal methods ───

    def _fetch_html(self, url, retries=3):
        for attempt in range(retries):
            try:
                resp = self.session.get(url, timeout=30, headers={"Referer": WECHAT_REFERER})
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
                elif attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
            except:
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
        return None

    @staticmethod
    def _check_page_valid(html):
        for kw in INVALID_PAGE_KEYWORDS:
            if kw in html:
                return False, kw
        return True, ""

    def _html_to_markdown(self, html):
        soup = BeautifulSoup(html, "lxml")
        valid, reason = self._check_page_valid(html)
        if not valid:
            return None, f"Invalid page: {reason}"

        self._remove_hidden_elements(soup)
        self._fix_bold_br(soup)
        self._fix_heading_br(soup)
        self._fix_datasrc_to_src(soup)  # KEY: WeChat data-src → src

        content_el = soup.select_one("#js_content") or soup.select_one(".rich_media_content")
        if not content_el:
            return None, "No content found"

        meta = self._extract_meta_wechat(soup)
        for tag in content_el.find_all(["script", "style", "mp-common-profile",
                                        "mp-style-type", "mpvoice", "mpvideosnap", "iframe"]):
            tag.decompose()

        md = markdownify.markdownify(
            str(content_el), heading_style="ATX",
            strip=["script", "style"],
            escape_asterisks=False, escape_underscores=False,
        )

        # Post-processing
        md = re.sub(r'\*\*\*', '**', md)
        md = re.sub(r'###(.+?)###', r'**\1**', md)
        lines = md.split('\n')
        fixed = []
        for line in lines:
            if line.count('**') % 2 == 1:
                line += '**'
            fixed.append(line)
        md = '\n'.join(fixed)

        for pat in [r'赞\b', r'分享\b', r'推荐\b', r'写留言\b', r'已分享至', r'分享到']:
            md = re.sub(pat, '', md)

        md = md.replace('\x0d\x0a', '\n').replace('\x0d', '\n').replace('\r\n', '\n')
        md = self._decode_entities(md)
        md = re.sub(r'^#+\s*$', '', md, flags=re.MULTILINE)
        md = re.sub(r'^\*\*\s*$', '', md, flags=re.MULTILINE)
        md = self._clean_wechat_hashtags(md)

        if not meta["description"]:
            desc = self._extract_fallback_description(md)
            if desc:
                meta["description"] = desc

        return {"markdown": md, "meta": meta}, None

    @staticmethod
    def _extract_meta_wechat(soup):
        meta = {}
        el = soup.select_one("#activity-name")
        meta["title"] = el.get_text(strip=True) if el else ""
        el = soup.select_one("#js_name")
        meta["author"] = el.get_text(strip=True) if el else ""
        el = soup.select_one("#publish_time")
        meta["publish_time"] = el.get_text(strip=True) if el else ""
        el = soup.select_one('meta[property="og:description"]')
        meta["description"] = el.get("content", "") if el else ""
        return meta

    @staticmethod
    def _remove_hidden_elements(soup):
        for el in soup.find_all(style=True):
            if el.attrs is None:
                continue
            style = el.get("style", "")
            if style and "display:none" in style.replace(" ", ""):
                el.decompose()

    @staticmethod
    def _fix_bold_br(soup):
        for tag_name in ["strong", "b", "em", "i"]:
            for tag in soup.find_all(tag_name):
                for br in tag.find_all("br"):
                    br.replace_with(NavigableString(" "))

    @staticmethod
    def _fix_heading_br(soup):
        for tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            for tag in soup.find_all(tag_name):
                for br in tag.find_all("br"):
                    br.replace_with(NavigableString(" "))

    @staticmethod
    def _fix_datasrc_to_src(soup):
        """Replace data-src with src for all img tags (WeChat uses data-src)."""
        for img in soup.find_all("img"):
            data_src = img.get("data-src", "")
            if data_src and not img.get("src"):
                img["src"] = data_src
            elif data_src and img.get("src", "") == "":
                img["src"] = data_src

    @staticmethod
    def _decode_entities(text):
        def replace_num(m):
            try: return chr(int(m.group(1)))
            except: return m.group(0)
        def replace_hex(m):
            try: return chr(int(m.group(1), 16))
            except: return m.group(0)
        text = re.sub(r'&#(\d+);', replace_num, text)
        text = re.sub(r'&#x([0-9a-fA-F]+);', replace_hex, text)
        named = {"&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">",
                 "&quot;": '"', "&apos": "'"}
        for entity, char in named.items():
            text = text.replace(entity, char)
        return text

    @staticmethod
    def _clean_wechat_hashtags(md):
        """Remove WeChat #hashtags from body (not frontmatter)."""
        parts = md.split('---\n', 2)
        if len(parts) >= 3:
            frontmatter = parts[0] + '---\n'
            body = parts[1] + '---\n' + parts[2] if len(parts) > 2 else parts[1]
        else:
            frontmatter = ''
            body = md
        body = re.sub(r'^#[^\s#]{1,20}$', '', body, flags=re.MULTILINE)
        body = re.sub(r'#([\u4e00-\u9fa5a-zA-Z0-9_]{2,15})', r'\1', body)
        body = re.sub(r'\n{3,}', '\n\n', body)
        return frontmatter + body if frontmatter else body

    @staticmethod
    def _extract_fallback_description(md):
        lines = md.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('!') or line.startswith('---'):
                continue
            if any(kw in line for kw in ['往期精彩', '扫码关注', '点击下方', '推荐阅读', '更多精彩']):
                continue
            if re.match(r'^!\[.*\]\(.*\)$', line) or re.match(r'^!\[\[.*\]\]$', line):
                continue
            if len(line) >= 20:
                return line[:200]
        return ""

    @staticmethod
    def _collect_images(html):
        soup = BeautifulSoup(html, "lxml")
        content_el = soup.select_one("#js_content") or soup.select_one(".rich_media_content")
        if not content_el:
            return []
        images = []
        seen = set()
        for img in content_el.find_all("img"):
            url = img.get("data-src") or img.get("src", "")
            if url and url.startswith("http") and url not in seen:
                seen.add(url)
                images.append(url)
        return images

    def _download_images(self, img_urls, save_dir, referer=WECHAT_REFERER):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        img_map = {}
        for url in img_urls:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            ext = "jpg"
            wx_fmt = re.search(r'wx_fmt=(\w+)', url)
            if wx_fmt:
                ext = wx_fmt.group(1).lower()
                if ext == "jpeg":
                    ext = "jpg"
            else:
                path_ext = os.path.splitext(urlparse(url).path)[1].lower().strip('.')
                if path_ext in ["jpg", "jpeg", "png", "gif", "webp", "bmp"]:
                    ext = path_ext
            filename = f"img-{url_hash}.{ext}"
            filepath = os.path.join(save_dir, filename)
            if not os.path.exists(filepath):
                try:
                    resp = self.session.get(url, timeout=15, headers={"Referer": referer})
                    if resp.status_code == 200:
                        with open(filepath, 'wb') as f:
                            f.write(resp.content)
                    else:
                        filename = None
                except:
                    filename = None
            img_map[url] = filename
        return img_map

    @staticmethod
    def _replace_image_urls(md, img_map):
        for url, local_name in img_map.items():
            if local_name:
                md = md.replace(url, f"attachments/{local_name}")
        return md

    def _build_note(self, title, url, author, account, publish_time,
                    description, content_md, category):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        tag_template = self.tag_map.get(category, self.tag_map.get("default"))
        tag = tag_template.format(category=category)
        if description:
            description = description.replace('\x0d\x0a', ' ').replace('\r\n', ' ').strip()
        return f"""---
title: {title}
source: {url}
author: {author}
account: {account}
publish_date: {publish_time}
date_saved: {now}
content_type: 公众号文章
tags:
  - 状态/待消化
  - {tag}
---

## 摘要
{description if description else "（无摘要）"}

## 正文
{content_md}

---
**来源**：[{title}]({url})
**公众号**：{account}
**剪藏时间**：{now}
"""

    @staticmethod
    def _sanitize_filename(title):
        name = re.sub(r'[<>:"/\\|?*\n\r\t]', '-', title.strip())
        name = re.sub(r'\s+', ' ', name)
        if len(name) > 80:
            name = name[:80]
        return name.strip('-').strip()

    def _save_to_vault(self, title, note, category):
        dir_path = os.path.join(self.output_base, category)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        filename = self._sanitize_filename(title) + ".md"
        filepath = os.path.join(dir_path, filename)
        if os.path.exists(filepath):
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{ts}{ext}"
            filepath = os.path.join(dir_path, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(note)
        return filepath

    def _load_existing_urls(self):
        if self._existing_urls is not None:
            return self._existing_urls
        result = self.scan_vault_urls()
        self._existing_urls = result["urls"]
        return self._existing_urls

    def _load_existing_titles(self):
        if self._existing_urls is not None:
            # scan_vault_urls also returns titles, but we store only urls
            # Re-scan for titles
            pass
        result = self.scan_vault_urls()
        self._existing_urls = result["urls"]
        return result["titles"]


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Web Clipper — 剪藏微信公众号文章到 Obsidian Vault")
    parser.add_argument("--url", help="Single URL to clip")
    parser.add_argument("--title", default="", help="Article title (for single URL mode)")
    parser.add_argument("--category", default="其他", help="Category subfolder name")
    parser.add_argument("--account", default="", help="WeChat account name")
    parser.add_argument("--batch", help="JSON file with article list for batch mode")
    parser.add_argument("--scan-vault", action="store_true", help="Scan Vault for existing URLs")
    parser.add_argument("--vault", help="Obsidian Vault path (auto-detect if omitted)")
    parser.add_argument("--base-dir", default="2-Projects/CRA学习文章", help="Output base directory in Vault")
    parser.add_argument("--no-images", action="store_true", help="Skip image download")
    parser.add_argument("--no-dedup", action="store_true", help="Skip dedup check")
    parser.add_argument("--rate", type=float, default=1.0, help="Rate limit between requests (seconds)")
    parser.add_argument("--update-moc", action="store_true", help="Update MOC navigation page")
    parser.add_argument("--moc-name", default="MOC-CRA学习文章", help="MOC file name (default: MOC-CRA学习文章)")
    parser.add_argument("--output", help="Save results to JSON file")
    args = parser.parse_args()

    clipper = WebClipper(
        vault_path=args.vault,
        base_dir=args.base_dir,
        download_images=not args.no_images,
        rate_limit=args.rate,
    )

    if args.scan_vault:
        result = clipper.scan_vault_urls()
        print(f"Scanned {result['total_files']} .md files")
        print(f"Found {len(result['urls'])} unique source URLs")
        print(f"Found {len(result['titles'])} unique titles")
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump({
                    "urls": sorted(list(result["urls"])),
                    "titles": sorted(list(result["titles"])),
                }, f, ensure_ascii=False, indent=2)
            print(f"Saved to: {args.output}")
        return

    if args.update_moc:
        WebClipper.update_moc(
            vault_path=args.vault or clipper.vault_path,
            base_dir=args.base_dir,
            moc_name=args.moc_name,
        )
        print(f"MOC 更新完成: {args.moc_name}")
        return

    if args.batch:
        with open(args.batch, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        # Filter to only articles with URLs
        if isinstance(articles, list) and articles and isinstance(articles[0], dict):
            to_clip = [a for a in articles if a.get("url") and a.get("status") != "skip"]
        else:
            print("Invalid batch file format. Expected list of dicts with 'url' key.")
            return

        print(f"Articles to clip: {len(to_clip)}", flush=True)
        results = clipper.clip_batch(
            to_clip,
            dedup=not args.no_dedup,
            dedup_titles=not args.no_dedup,
        )
        ok = sum(1 for r in results if r.get("success"))
        fail = len(results) - ok
        print(f"\n{'='*60}\nClipping complete!\n  Success: {ok}\n  Failed:  {fail}\n  Total:  {len(results)}")

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"Results saved to: {args.output}")
        return

    if args.url:
        result = clipper.clip_url(args.url, title=args.title, category=args.category, account=args.account)
        if result["success"]:
            print(f"OK: {result['file_path']}")
        else:
            print(f"FAIL: {result['error']}")
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
