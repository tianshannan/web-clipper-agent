#!/usr/bin/env python3
"""
Web Clipper Agent v5.0 — 合并 v3.2（文本处理优势）+ v4.0（类架构 + 高级功能）

v5.0 合并要点：
  - WebClipper 类（v4.0）作为容器，支持可配置 vault_path / base_dir / tag_map
  - v3.2 全部文本处理：文件名彻底清理、表格优先解析、相对链接补全、
    图片占位符系统、16 步 Markdown 后处理、摘要回退、元信息转义清理
  - v4.0 高级功能：扫描去重、分类写入、MOC 导航页、质量评分、CRA 自动分类、argparse CLI
  - Vault 路径更新为 E:\\OneDrive\\陈小虎同学
  - 默认输出 1-Inbox，--category + --base-dir 时按分类写入
  - browser headless 降级 fallback（v3.2）
  - 兼容 v3.2 函数式 API（clip_url / clip_batch）

版本历史：
  v3   requests 直接抓取 + 表格优先 + 图片本地化 + P.A.I.R v5
  v3.1 隐藏元素过滤 + 图片 hash 去重 + 相对链接补全 + 请求重试 + Session 复用
  v3.2 失效页面检测 + bold/heading br 修复 + 摘要回退 + 时间精确到分钟 + 转义清理
  v4.0 WebClipper 类 + 扫描去重 + 分类写入 + MOC + filter_and_classify + argparse CLI
  v5.0 合并 v3.2 + v4.0 全部优势
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import datetime
from collections import defaultdict
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import markdownify

# ============================================================
# 版本号（用于 GitHub 版本对比）
# ============================================================
VERSION = "5.0"
GITHUB_REPO = "tianshannan/web-clipper-agent"
GITHUB_RAW_VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/scripts/clip.py"

# ============================================================
# 常量（合并 v3.2 + v4.0）
# ============================================================

WECHAT_REFERER = "https://mp.weixin.qq.com/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

MAX_RETRIES = 3
RETRY_BASE_INTERVAL = 2
REQUEST_TIMEOUT = 30

# v3.2 失效页面检测关键词（更完整）
PAGE_FAILURE_PATTERNS = [
    "该内容已被发布者删除",
    "此内容因违规无法查看",
    "当前环境异常",
    "完成验证后即可继续访问",
    "该公众号已迁移",
    "此帐号已自主注销",
]

# v4.0 失效页面检测关键词（补充）
INVALID_PAGE_KEYWORDS = [
    "已被发布者删除", "违规无法查看", "当前环境异常",
    "完成验证后即可继续访问", "公众号已迁移", "账号已注销",
    "环境异常", "访问过于频繁",
]

# 摘要回退时跳过的推广段落关键词
SUMMARY_SKIP_PATTERNS = [
    r'^\s*\**\s*(往期|推荐阅读|延伸阅读|往期精彩)',
    r'^\s*\**\s*(戳|关注|回复关键词|扫码|长按识别|加入社群|点击下方)',
]

# v4.0 标签映射
DEFAULT_TAG_MAP = {
    "default": "A/临床试验监查/{category}",
    "CRA职业发展": "A/个人成长",
}

# v4.0 质量评分关键词
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

# v4.0 排除非学习内容
EXCLUDE_PATTERNS = [
    "招聘", "招人", "诚聘", "岗位", "求职", "简历", "面试",
    "培训通知", "会议通知", "会议日程", "大会", "峰会", "论坛通知",
    "广告", "推广", "优惠", "活动", "抽奖", "福利",
    "患者招募", "受试者招募", "入组通知",
    "节日", "新年", "中秋", "国庆", "春节", "元旦", "端午",
    "开工大吉", "放假", "休息", "温馨提示", "关注公众号", "扫码", "二维码",
]

# v4.0 CRA 分类关键词
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

# 默认 Vault 路径
DEFAULT_VAULT_PATH = r"E:\OneDrive\陈小虎同学"
DEFAULT_INBOX_DIR = "1-Inbox"
DEFAULT_BASE_DIR = "2-Projects/CRA学习文章"
ATTACHMENTS_DIR = "attachments"

# 全局 Session（复用连接池）
_session = None

# 全局图片缓存：url_hash → 本地文件路径（跨文章去重）
_image_cache = {}


def _get_session():
    """获取全局 requests.Session（连接池复用）"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
    return _session


# ============================================================
# WebClipper 类（v4.0 架构 + v3.2 全部文本处理）
# ============================================================

class WebClipper:
    """网页剪藏引擎 — 抓取、解析、转换、保存。"""

    def __init__(self, vault_path=None, base_dir=None, tag_map=None,
                 download_images=True, rate_limit=1.0):
        """
        Args:
            vault_path: Obsidian Vault 根路径。None 则自动检测。
            base_dir: Vault 内子目录。None 则使用 1-Inbox。
            tag_map: 分类→标签映射。None 使用默认 P.A.I.R v5。
            download_images: 是否下载图片到本地。
            rate_limit: 请求间隔秒数。
        """
        self.vault_path = vault_path or self._detect_vault_path()
        self.base_dir = base_dir  # None = 1-Inbox 模式
        self.tag_map = tag_map or DEFAULT_TAG_MAP
        self.download_images_flag = download_images
        self.rate_limit = rate_limit
        self._existing_urls = None
        self._existing_titles = None

        self.session = _get_session()

    @staticmethod
    def _detect_vault_path():
        """从 obsidian.json 自动检测 Vault 路径，优先 open=True 的 Vault。"""
        config_path = os.path.expandvars(r"%APPDATA%\Obsidian\obsidian.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                vaults = config.get("vaults", {})
                for vid, vinfo in vaults.items():
                    if vinfo.get("open") and vinfo.get("path") and os.path.exists(vinfo["path"]):
                        return vinfo["path"]
                for vid, vinfo in vaults.items():
                    path = vinfo.get("path", "")
                    if path and os.path.exists(path):
                        return path
            except (json.JSONDecodeError, IOError):
                pass
        # Fallback: 当前已知路径
        for p in [DEFAULT_VAULT_PATH,
                  r"D:\BaiduSyncdisk\陈小虎同学",
                  r"C:\Users\陈虎\Nutstore\1\陈小虎同学"]:
            if os.path.exists(p):
                return p
        return DEFAULT_VAULT_PATH

    # ─── 公开 API ───

    def clip_url(self, url, title=None, category=None, account="",
                 download_imgs=None):
        """
        剪藏单个 URL。

        Args:
            url: 文章 URL
            title: 可选标题覆盖
            category: 分类（如"知情同意"）。None 则写入 1-Inbox。
            account: 公众号名称
            download_imgs: 是否下载图片（None 使用实例配置）

        Returns:
            dict: {success, file_path, title, author, ...}
        """
        if download_imgs is None:
            download_imgs = self.download_images_flag

        is_wechat = "mp.weixin.qq.com" in url
        referer = WECHAT_REFERER if is_wechat else url

        # --- Step 1: 抓取 HTML ---
        html = None
        source_method = "requests"
        try:
            html = self._fetch_html(url)
            if not html or len(html) < 500:
                raise ValueError("HTML 内容过短，可能被拦截")
        except Exception as e:
            try:
                html = self._fetch_html_browser(url)
                source_method = "browser"
            except Exception as e2:
                return {"success": False,
                        "error": f"requests 和 browser 均失败: {e}; {e2}",
                        "title": title or ""}

        # --- Step 0: 失效页面检测 ---
        if self._detect_page_failure(html):
            return {"success": False,
                    "error": "页面已失效（被删除/违规/验证拦截/账号注销），不产出内容",
                    "title": title or ""}

        # --- Step 2: 解析元信息 ---
        soup = BeautifulSoup(html, 'lxml')

        if is_wechat:
            meta = self._extract_meta_wechat(soup)
        else:
            meta = self._extract_meta_generic(soup, url)

        article_title = meta.get('title', '') or title or '未命名'
        author = meta.get('author', '')
        acct = meta.get('account', '') or account
        pub_date = meta.get('publish_date', '')
        description = meta.get('description', '')

        # 元信息转义清理
        article_title = self._clean_escape(article_title)
        author = self._clean_escape(author) if author else ''
        acct = self._clean_escape(acct) if acct else ''
        description = self._clean_escape(description) if description else ''

        # --- Step 2.5: 无关元素移除 + 相对链接补全 ---
        self._remove_unwanted_elements(soup)
        self._fix_relative_links(soup, url)

        # 提取正文元素
        content_el = self._extract_content_element(soup, is_wechat)
        if not content_el:
            return {"success": False, "error": "无法提取正文内容",
                    "title": article_title}

        # 在正文范围内清理隐藏元素
        content_soup = BeautifulSoup(str(content_el), 'lxml')
        self._remove_hidden_elements(content_soup)

        # --- Step 2.6: 粗体/斜体内部 <br> 合并 + 标题内 <br> 压缩 ---
        self._merge_inline_br(content_soup)

        # --- Step 2.7: data-src → src（微信懒加载） ---
        self._fix_datasrc_to_src(content_soup)

        # --- Step 3: 表格优先解析 ---
        content_html = self._parse_tables_first(content_soup)

        # --- Step 4: 图片处理 ---
        img_urls = self._collect_images(content_html)
        content_html = self._replace_images_with_placeholders(content_html, img_urls)

        # --- Step 5: HTML → Markdown（16 步后处理） ---
        content_md = self._html_to_markdown(content_html)

        # --- 图片下载 & 回填 ---
        img_map = {}
        img_failed = []
        if download_imgs and img_urls:
            attachments_path = os.path.join(self.vault_path, ATTACHMENTS_DIR)
            os.makedirs(attachments_path, exist_ok=True)
            dl_result = self._download_images(img_urls, attachments_path, referer)
            img_map = dl_result['ok']
            img_failed = dl_result['failed']

        content_md = self._restore_image_placeholders(content_md, img_map)

        # 清理残留空图片标签
        content_md = re.sub(r'!\[\]\(\)', '', content_md)
        content_md = re.sub(r'\n{3,}', '\n\n', content_md)

        # --- Step 6: 微信 #标签清理 ---
        if is_wechat:
            content_md = self._clean_wechat_hashtags(content_md)

        # --- Step 7: 构建 & 保存 ---
        content_type = "公众号文章" if is_wechat else "网页剪藏"
        note = self._build_note(
            title=article_title, url=url, author=author, account=acct,
            pub_date=pub_date, description=description,
            content_md=content_md, content_type=content_type, category=category,
        )
        filepath = self._save_to_vault(article_title, note, category)

        return {
            "success": True,
            "file_path": filepath,
            "title": article_title,
            "author": author,
            "account": acct,
            "publish_date": pub_date,
            "content_type": content_type,
            "content_length": len(content_md),
            "image_total": len(img_urls),
            "image_downloaded": len(img_map),
            "image_failed": len(img_failed),
            "fetch_method": source_method,
        }

    def clip_batch(self, articles, dedup=True, dedup_titles=True):
        """
        批量剪藏。

        Args:
            articles: dict 列表，含 url/title/category/account/folder
            dedup: 跳过 Vault 中已存在的 URL
            dedup_titles: 跳过 Vault 中已存在的标题

        Returns:
            结果 dict 列表
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
            category = article.get("category") or article.get("primary_category")
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
        """扫描 Vault 中已有的 source URL 和标题（用于去重）。"""
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
                except Exception:
                    pass
        return {"urls": url_set, "titles": title_set, "total_files": count}

    @staticmethod
    def filter_and_classify(articles, top_n=15):
        """筛选 CRA 学习价值文章并自动分类。"""
        seen = set()
        deduped = []
        for a in articles:
            title = a.get("title", "").strip()
            if not title or len(title) < 4 or title in seen:
                continue
            seen.add(title)
            deduped.append(a)

        exclude_re = re.compile('|'.join(EXCLUDE_PATTERNS))
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
    def update_moc(vault_path, base_dir=DEFAULT_BASE_DIR, moc_name="MOC-CRA学习文章"):
        """更新 MOC 导航页。"""
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
                except Exception:
                    pass
                categories[rel_dir].append(title)

        total = sum(len(v) for v in categories.values())
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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
            articles_list = sorted(categories[cat])
            moc += f"## {cat}（{len(articles_list)}篇）\n\n"
            for title in articles_list:
                filename = re.sub(r'[<>:"/\\|?*]', '-', title.strip())[:80]
                moc += f"- [[{filename}]]\n"
            moc += "\n"

        moc_path = os.path.join(cra_base, f"{moc_name}.md")
        with open(moc_path, 'w', encoding='utf-8') as f:
            f.write(moc)
        return moc_path

    # ─── 内部方法：抓取 ───

    def _fetch_html(self, url, timeout=REQUEST_TIMEOUT):
        """requests Session 抓取 HTML，失败重试 MAX_RETRIES 次。"""
        session = _get_session()
        headers = {}
        if "mp.weixin.qq.com" in url:
            headers["Referer"] = WECHAT_REFERER

        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.get(url, headers=headers, timeout=timeout,
                                   allow_redirects=True)
                resp.encoding = resp.apparent_encoding or 'utf-8'
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
                last_error = f"HTTP {resp.status_code} 或内容过短"
            except requests.exceptions.RequestException as e:
                last_error = str(e)

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_INTERVAL * attempt)

        raise ValueError(f"requests 抓取失败（重试 {MAX_RETRIES} 次）: {last_error}")

    @staticmethod
    def _fetch_html_browser(url):
        """browser headless 模式抓取（fallback）。"""
        sys.path.insert(0, os.path.join(os.getenv("SKILL_PATH", ""),
                                        "browser", "scripts"))
        import browser
        browser.mode = "headless"
        browser.navigate(url)
        time.sleep(3)
        js = "return document.documentElement.outerHTML"
        result = browser.execute_script(js)
        if result.startswith('execute_script'):
            result = result.split('\n', 1)[1] if '\n' in result else result
        return result

    @staticmethod
    def _detect_page_failure(html):
        """检测页面是否失效（删除/违规/验证页/注销）。"""
        all_patterns = PAGE_FAILURE_PATTERNS + INVALID_PAGE_KEYWORDS
        for pattern in all_patterns:
            if pattern in html:
                return True
        return False

    # ─── 内部方法：元信息提取 ───

    @staticmethod
    def _extract_meta_wechat(soup):
        """提取微信公众号文章元信息（v3.2：var ct 时间戳精确到分钟）。"""
        meta = {}

        # 标题
        og_title = soup.find('meta', property='og:title')
        if og_title:
            meta['title'] = og_title.get('content', '').strip()
        if not meta.get('title'):
            t = soup.find(id='activity-name') or soup.find(class_='rich_media_title')
            if t:
                meta['title'] = t.get_text(strip=True)

        # 作者
        m_author = soup.find('meta', attrs={'name': 'author'})
        if m_author:
            meta['author'] = m_author.get('content', '').strip()
        if not meta.get('author'):
            js_author = soup.find(id='js_author_name')
            if js_author:
                meta['author'] = js_author.get_text(strip=True)

        # 公众号名
        js_name = soup.find(id='js_name')
        if js_name:
            meta['account'] = js_name.get_text(strip=True)

        # 发布时间：var ct = "时间戳" → 精确到分钟
        for script in soup.find_all('script'):
            text = script.string or script.get_text()
            if text and 'var ct' in text:
                m = re.search(r'var\s+ct\s*=\s*["\'](\d+)["\']', text)
                if m:
                    ts = int(m.group(1))
                    meta['publish_date'] = datetime.datetime.fromtimestamp(
                        ts).strftime('%Y-%m-%d %H:%M')
                    break
        if not meta.get('publish_date'):
            pt = soup.find(id='publish_time')
            if pt:
                raw = pt.get_text(strip=True)
                m = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?\s*(\d{1,2}:\d{2})?', raw)
                if m:
                    date_part = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                    time_part = f" {m.group(4)}" if m.group(4) else ""
                    meta['publish_date'] = date_part + time_part
        if not meta.get('publish_date'):
            m = re.search(r'publish_time=(\d+)', str(soup))
            if m:
                ts = int(m.group(1))
                meta['publish_date'] = datetime.datetime.fromtimestamp(
                    ts).strftime('%Y-%m-%d %H:%M')

        # 描述
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            meta['description'] = og_desc.get('content', '').strip()

        return meta

    @staticmethod
    def _extract_meta_generic(soup, url):
        """提取通用网页元信息。"""
        meta = {}
        og_title = soup.find('meta', property='og:title')
        if og_title:
            meta['title'] = og_title.get('content', '').strip()
        if not meta.get('title'):
            h1 = soup.find('h1')
            if h1:
                meta['title'] = h1.get_text(strip=True)
        if not meta.get('title'):
            meta['title'] = soup.title.get_text(strip=True) if soup.title else '未命名'

        m_author = soup.find('meta', attrs={'name': 'author'})
        if m_author:
            meta['author'] = m_author.get('content', '').strip()

        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            meta['description'] = og_desc.get('content', '').strip()
        if not meta.get('description'):
            m_desc = soup.find('meta', attrs={'name': 'description'})
            if m_desc:
                meta['description'] = m_desc.get('content', '').strip()

        return meta

    # ─── 内部方法：HTML 预处理 ───

    @staticmethod
    def _remove_hidden_elements(soup):
        """移除 display:none 的隐藏元素（不移除 visibility:hidden）。"""
        for el in soup.find_all(True):
            if not el.attrs:
                continue
            style = el.attrs.get('style', '')
            if style:
                if re.search(r'display\s*:\s*none', style, re.IGNORECASE):
                    el.decompose()

    @staticmethod
    def _remove_unwanted_elements(soup):
        """移除不需要的元素（script/style/nav/footer/广告等）。"""
        for selector in ['script', 'style', 'noscript', 'nav', 'footer',
                         'iframe', 'mp-common-profile', 'mp-style-type',
                         'mpvoice', 'mpvideosnap']:
            for el in soup.find_all(selector):
                el.decompose()
        for cls in ['qr_code_pc', 'reward_area', 'qr_code_super',
                    'recommend_area', 'gallery_layout', 'ad_area']:
            for el in soup.find_all(class_=cls):
                el.decompose()

    @staticmethod
    def _fix_relative_links(soup, base_url):
        """将相对链接补全为绝对 URL。"""
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href and not href.startswith(('http://', 'https://', 'mailto:',
                                             '#', 'javascript:', 'tel:')):
                a['href'] = urljoin(base_url, href)
        for img in soup.find_all('img'):
            for attr in ['src', 'data-src']:
                val = img.get(attr)
                if val and not val.startswith(('http://', 'https://', 'data:')):
                    img[attr] = urljoin(base_url, val)

    @staticmethod
    def _extract_content_element(soup, is_wechat):
        """提取正文元素。"""
        if is_wechat:
            return (soup.find(id='js_content') or
                    soup.find(class_='rich_media_content'))
        else:
            for selector in ['article', '.post-content', '.article-content',
                             'main', '.content', '#content']:
                el = soup.select_one(selector)
                if el:
                    return el
        return soup.body or soup

    @staticmethod
    def _merge_inline_br(soup_content):
        """粗体/斜体内部 <br> 合并 + 标题内 <br> 压缩。"""
        for tag_name in ['strong', 'b', 'em', 'i']:
            for el in soup_content.find_all(tag_name):
                for br in el.find_all('br'):
                    br.replace_with(NavigableString(' '))
        for i in range(1, 7):
            for el in soup_content.find_all(f'h{i}'):
                for br in el.find_all('br'):
                    br.replace_with(NavigableString(' '))

    @staticmethod
    def _fix_datasrc_to_src(soup):
        """微信 data-src → src（懒加载修复）。"""
        for img in soup.find_all('img'):
            data_src = img.get('data-src', '')
            if data_src and not img.get('src'):
                img['src'] = data_src

    @staticmethod
    def _parse_tables_first(soup_content):
        """表格优先解析为 Markdown（保证单元格内 <br> 不拆行）。"""
        for table in soup_content.find_all('table'):
            rows = table.find_all('tr')
            if not rows:
                continue
            md_lines = []
            max_cols = 0
            for row in rows:
                cells = row.find_all(['td', 'th'])
                cell_texts = []
                for cell in cells:
                    for br in cell.find_all('br'):
                        br.replace_with(' ')
                    text = cell.get_text(separator=' ', strip=True)
                    text = text.replace('|', '\\|').replace('\n', ' ')
                    text = re.sub(r'\s+', ' ', text).strip()
                    cell_texts.append(text if text else ' ')
                max_cols = max(max_cols, len(cell_texts))
                md_lines.append(cell_texts)
            if not md_lines:
                continue
            for line in md_lines:
                while len(line) < max_cols:
                    line.append(' ')
            md_table = '\n\n'
            for i, line in enumerate(md_lines):
                md_table += '| ' + ' | '.join(line) + ' |\n'
                if i == 0:
                    md_table += '|' + ' --- |' * max_cols + '\n'
            md_table += '\n'
            table.replace_with(NavigableString(md_table))
        return str(soup_content)

    # ─── 内部方法：图片处理 ───

    @staticmethod
    def _collect_images(html):
        """从 HTML 中收集图片 URL（微信 data-src + 通用 src）。"""
        img_urls = []
        seen = set()
        for m in re.finditer(r'data-src="([^"]+)"', html):
            url = m.group(1)
            if url.startswith('http') and url not in seen:
                seen.add(url)
                img_urls.append(url)
        for m in re.finditer(r'<img[^>]+src="(https?://[^"]+)"', html):
            url = m.group(1)
            if url not in seen:
                seen.add(url)
                img_urls.append(url)
        return img_urls

    @staticmethod
    def _replace_images_with_placeholders(html, img_urls):
        """将 HTML 中的 <img> 标签替换为 Unicode 占位符。"""
        url_to_idx = {url: i + 1 for i, url in enumerate(img_urls)}

        def replace_img(match):
            tag = match.group(0)
            url = None
            m = re.search(r'data-src="([^"]+)"', tag)
            if m:
                url = m.group(1)
            else:
                m = re.search(r'src="(https?://[^"]+)"', tag)
                if m:
                    url = m.group(1)
            if url and url in url_to_idx:
                return f'\uFFF9IMG{url_to_idx[url]}\uFFFA'
            return ''

        return re.sub(r'<img[^>]*?>', replace_img, html)

    def _download_images(self, img_urls, save_dir, referer=WECHAT_REFERER):
        """下载图片到 save_dir，hash 去重命名，跨文章缓存。"""
        os.makedirs(save_dir, exist_ok=True)
        result = {'ok': {}, 'failed': []}
        session = _get_session()
        headers = {"Referer": referer}

        for i, url in enumerate(img_urls, 1):
            h = self._url_hash(url)
            if h in _image_cache:
                result['ok'][i] = _image_cache[h]
                continue

            ext = self._get_ext_from_url(url)
            filename = f"img-{h}.{ext}"
            filepath = os.path.join(save_dir, filename)
            ref_path = f"{ATTACHMENTS_DIR}/{filename}"

            if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
                result['ok'][i] = ref_path
                _image_cache[h] = ref_path
                continue

            downloaded = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    resp = session.get(url, headers=headers, timeout=30)
                    if resp.status_code == 200 and len(resp.content) > 100:
                        with open(filepath, 'wb') as f:
                            f.write(resp.content)
                        if os.path.getsize(filepath) > 100:
                            result['ok'][i] = ref_path
                            _image_cache[h] = ref_path
                            downloaded = True
                            break
                except requests.exceptions.RequestException:
                    pass
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BASE_INTERVAL * attempt)

            if not downloaded:
                if os.path.exists(filepath) and os.path.getsize(filepath) <= 100:
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                result['failed'].append(url)
            time.sleep(0.3)

        return result

    @staticmethod
    def _restore_image_placeholders(md, img_map):
        """将占位符替换为 Obsidian ![[attachments/img.png]] 本地引用。"""
        def replace(match):
            idx = int(match.group(1))
            if idx in img_map:
                return f"![[{img_map[idx]}]]"
            return f"<!-- 图片下载失败 #{idx} -->"
        return re.sub(r'\uFFF9IMG(\d+)\uFFFA', replace, md)

    @staticmethod
    def _url_hash(url, length=12):
        return hashlib.md5(url.encode('utf-8')).hexdigest()[:length]

    @staticmethod
    def _get_ext_from_url(url):
        if not url:
            return 'jpg'
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if 'wx_fmt' in params:
            fmt = params['wx_fmt'][0].lower()
            return 'jpg' if fmt == 'jpeg' else fmt
        path = parsed.path
        m = re.search(r'\.([a-zA-Z]{2,4})$', path)
        if m:
            return m.group(1).lower()
        return 'jpg'

    # ─── 内部方法：HTML → Markdown（16 步后处理） ───

    @staticmethod
    def _html_to_markdown(html):
        """HTML → 格式良好的 Markdown（v3.2 完整 16 步后处理）。"""
        md = markdownify.markdownify(
            html,
            heading_style="ATX",
            strip=['script', 'style', 'mp-common-profile', 'mp-style-type',
                   'mpvoice', 'mpvideosnap', 'iframe', 'noscript'],
            bullets='-',
            escape_asterisks=False,
            escape_underscores=False,
        )

        # 1. Fix ***text*** -> **text**
        md = re.sub(r'\*{3,}(.+?)\*{3,}', r'**\1**', md)
        md = re.sub(r'\*{2,}(.+?)\*{2,}', r'**\1**', md)

        # 2. Remove trailing *** from lines
        md = re.sub(r'\*{2,}$', '', md, flags=re.MULTILINE)
        md = re.sub(r'\*{2,}\n', '\n', md)

        # 3. Remove inline ### that aren't at line start -> convert to bold
        lines = md.split('\n')
        fixed_lines = []
        for line in lines:
            if '###' in line and not line.strip().startswith('#'):
                line = re.sub(r'#{2,}\s*', '**', line)
                if line.count('**') % 2 == 1:
                    line = line + '**'
            fixed_lines.append(line)
        md = '\n'.join(fixed_lines)

        # 4. Fix unpaired ** per line
        lines = md.split('\n')
        fixed_lines = []
        for line in lines:
            if line.count('**') % 2 == 1:
                line = line + '**'
            fixed_lines.append(line)
        md = '\n'.join(fixed_lines)

        # 5. Remove empty bold ****
        md = md.replace('****', '')

        # 6. Clean up \x0d\x0a escape characters
        md = md.replace('\\x0d\\x0a', '')
        md = md.replace('\x0d\x0a', '')
        md = md.replace('\\r\\n', '')
        md = md.replace('\r\n', '\n')

        # 7. Decode HTML numeric entities
        md = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), md)
        md = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), md)
        md = md.replace('&nbsp;', ' ').replace('&amp;', '&')
        md = md.replace('&lt;', '<').replace('&gt;', '>')
        md = md.replace('&quot;', '"').replace('&#39;', "'")

        # 8. Remove empty links
        md = re.sub(r'\[\s*\]\(\s*\)', '', md)

        # 9. Remove trailing whitespace per line
        md = '\n'.join(line.rstrip() for line in md.split('\n'))

        # 10. Fix list items that became headings
        md = re.sub(r'^(-\s*)#{1,6}\s+', r'\1**', md, flags=re.MULTILINE)

        # 11. Remove empty heading markers
        md = re.sub(r'^#{1,6}\s*$', '', md, flags=re.MULTILINE)

        # 12. Remove decorative headings (only bold markers, no content)
        md = re.sub(r'^#{1,6}\s*\*{0,2}\s*$', '', md, flags=re.MULTILINE)

        # 13. Remove lone/decorative bold-marker lines
        md = re.sub(r'^\s*\*{2,}\s*$', '', md, flags=re.MULTILINE)

        # 14. Remove empty bold pairs stuck at line ends
        md = re.sub(r'\*{4,}\s*$', '', md, flags=re.MULTILINE)

        # 15. Clean up space around bold markers
        md = re.sub(r'(?<!\S)\*\*[ \t]+(?=\S)', '**', md)
        md = re.sub(r'(\S)[ \t]+\*\*(?!\S)', r'\1**', md)

        # 16. Clean up excessive blank lines
        md = re.sub(r'\n{3,}', '\n\n', md).strip()

        return md

    # ─── 内部方法：微信 #标签清理 ───

    @staticmethod
    def _clean_wechat_hashtags(md):
        """清除微信正文末尾的 #话题标签（不影响 frontmatter）。"""
        lines = md.split('\n')
        cleaned = []
        for line in lines:
            if re.match(r'^\s*(#[\u4e00-\u9fa5A-Za-z]{2,10}\s*)+$', line):
                continue
            line = re.sub(r'#([\u4e00-\u9fa5A-Za-z]{2,10})(?=\s|$)', '', line)
            cleaned.append(line)
        return '\n'.join(cleaned)

    # ─── 内部方法：摘要回退 ───

    @staticmethod
    def _summary_fallback(content_md, max_len=200):
        """无 og:description 时取正文首个有效段落作为摘要。"""
        for para in content_md.split('\n\n'):
            raw = para.strip()
            if not raw:
                continue
            p = raw
            p = re.sub(r'!\[\[[^\]]*\]\]', '', p)
            p = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', p)
            p = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', p)
            p = re.sub(r'[*#>|`]', '', p)
            p = re.sub(r'\s+', ' ', p).strip()
            if len(p) < 20:
                continue
            skip = False
            for pattern in SUMMARY_SKIP_PATTERNS:
                if re.match(pattern, p):
                    skip = True
                    break
            if skip:
                continue
            if re.match(r'^(!\[\[[^\]]*\]\]\s*)+$', raw) or \
               re.match(r'^(!\[[^\]]*\]\([^)]*\)\s*)+$', raw):
                continue
            if re.match(r'^(\[[^\]]*\]\([^)]*\)\s*)+$', raw):
                continue
            if len(p) > max_len:
                return p[:max_len] + "……"
            return p
        return ""

    # ─── 内部方法：构建笔记 ───

    @staticmethod
    def _clean_escape(text):
        """清理转义字符和 HTML 实体。"""
        if not text:
            return text
        text = text.replace(r'\x0d\x0a', ' ')
        text = text.replace('\x0d\x0a', ' ')
        text = text.replace('\r\n', ' ')
        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
        text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        return text.strip()

    def _build_note(self, title, url, author, account, pub_date,
                    description, content_md, content_type, category=None):
        """按 P.A.I.R v5 模板格式化 Markdown 笔记。"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # 摘要回退
        if not description:
            description = self._summary_fallback(content_md)
        if not description:
            description = "（无摘要）"

        # 清理摘要中的转义字符
        description = self._clean_escape(description)
        description = re.sub(r'\s+', ' ', description).strip()

        # 构建标签
        tags = ["状态/待消化"]
        if category and self.base_dir:
            tag_template = self.tag_map.get(category, self.tag_map.get("default"))
            tag = tag_template.format(category=category)
            tags.append(tag)

        tags_yaml = '\n'.join(f"  - {t}" for t in tags)

        # 构建 source info
        source_lines = [f"**来源**：[{title}]({url})"]
        if author:
            source_lines.append(f"**作者**：{author}")
        if account:
            source_lines.append(f"**公众号**：{account}")
        if pub_date:
            source_lines.append(f"**发布日期**：{pub_date}")
        source_lines.append(f"**剪藏时间**：{now}")
        source_info = '\n'.join(source_lines)

        return f"""---
title: {title}
source: {url}
author: {author}
account: {account}
publish_date: {pub_date}
date_saved: {now}
content_type: {content_type}
tags:
{tags_yaml}
---

## 摘要

{description}

## 正文

{content_md}

---

{source_info}
"""

    @staticmethod
    def _sanitize_filename(name, max_len=80):
        """清理文件名中的非法字符（Windows + OneDrive 兼容）。"""
        name = re.sub(r'[/\\:*?"<>|]', '-', name).strip()
        name = name.replace('\u201c', "'").replace('\u201d', "'")
        name = name.replace('\u2018', "'").replace('\u2019', "'")
        name = name.replace('\u258e', '-')
        name = name.replace('\u2551', '|')
        name = name.replace('\u2016', '|')
        name = name.replace('\u2502', '|')
        name = name.replace('\u2236', ':')
        name = name.replace('\u2014', '-')
        name = name.replace('\u2013', '-')
        name = name.replace('\u2026', '...')
        name = name.replace('\u00b7', '-')
        name = name.replace('\u30fb', '-')
        name = name.replace('\u318d', '-')
        name = name.replace('\u2260', '!=')
        name = name.replace('\u200b', '')
        name = re.sub(r'[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef a-zA-Z0-9\-_.()\[\],!?:;\'\u201c\u201d\u2018\u2019\u3001\u3010\u3011\u2014\u2026\uff01\uff1f\uff1a\uff0c\uff1b\u300a\u300b\u3010\u3011]', '', name)
        name = re.sub(r' {2,}', ' ', name)
        name = re.sub(r'-{2,}', '-', name)
        name = name.strip('. ')
        if not name:
            name = 'untitled'
        if len(name) > max_len:
            name = name[:max_len].rstrip()
        return name

    def _save_to_vault(self, title, note, category=None):
        """保存笔记到 Vault。有 category+base_dir 时按分类写入，否则写入 1-Inbox。"""
        if category and self.base_dir:
            dir_path = os.path.join(self.vault_path, self.base_dir, category)
        else:
            dir_path = os.path.join(self.vault_path, DEFAULT_INBOX_DIR)
        os.makedirs(dir_path, exist_ok=True)

        filename = self._sanitize_filename(title) + ".md"
        filepath = os.path.join(dir_path, filename)

        if os.path.exists(filepath):
            ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{ts}{ext}"
            filepath = os.path.join(dir_path, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(note)
        return filepath

    # ─── 内部方法：去重 ───

    def _load_existing_urls(self):
        if self._existing_urls is not None:
            return self._existing_urls
        result = self.scan_vault_urls()
        self._existing_urls = result["urls"]
        self._existing_titles = result["titles"]
        return self._existing_urls

    def _load_existing_titles(self):
        if self._existing_titles is not None:
            return self._existing_titles
        result = self.scan_vault_urls()
        self._existing_urls = result["urls"]
        self._existing_titles = result["titles"]
        return self._existing_titles


# ============================================================
# 模块级兼容 API（v3.2 函数式调用方式）
# ============================================================

_default_clipper = None


def _get_default_clipper():
    global _default_clipper
    if _default_clipper is None:
        _default_clipper = WebClipper()
    return _default_clipper


def clip_url(url, download_imgs=True, use_browser_fallback=True):
    """v3.2 兼容接口：剪藏单个 URL 到 1-Inbox。"""
    clipper = _get_default_clipper()
    return clipper.clip_url(url, download_imgs=download_imgs)


def clip_batch(urls, download_imgs=True, interval=1.0):
    """v3.2 兼容接口：批量剪藏 URL 列表。"""
    clipper = _get_default_clipper()
    articles = [{"url": u} for u in urls]
    return clipper.clip_batch(articles, dedup=False, dedup_titles=False)


def clip_with_browser(url):
    """兼容旧版接口。"""
    return clip_url(url)


# ============================================================
# CLI（v4.0 argparse + v3.2 -f 兼容）
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Web Clipper Agent v5.0 — 剪藏网页到 Obsidian Vault")
    parser.add_argument("--url", help="单篇 URL")
    parser.add_argument("--title", default="", help="文章标题（单篇模式）")
    parser.add_argument("--category", default=None, help="分类子目录名")
    parser.add_argument("--account", default="", help="公众号名称")
    parser.add_argument("--batch", help="JSON 文件批量模式")
    parser.add_argument("-f", "--file", dest="url_file", help="URL 列表文件（每行一个）")
    parser.add_argument("--scan-vault", action="store_true", help="扫描 Vault 已有 URL")
    parser.add_argument("--vault", help="Obsidian Vault 路径（省略则自动检测）")
    parser.add_argument("--base-dir", default=None, help="输出子目录（默认 1-Inbox）")
    parser.add_argument("--no-images", action="store_true", help="跳过图片下载")
    parser.add_argument("--no-dedup", action="store_true", help="跳过去重检查")
    parser.add_argument("--rate", type=float, default=1.0, help="请求间隔秒数")
    parser.add_argument("--update-moc", action="store_true", help="更新 MOC 导航页")
    parser.add_argument("--moc-name", default="MOC-CRA学习文章", help="MOC 文件名")
    parser.add_argument("--output", help="结果保存到 JSON 文件")
    parser.add_argument("--version", action="store_true", help="显示版本号")
    args = parser.parse_args()

    if args.version:
        print(f"Web Clipper Agent v{VERSION}")
        print(f"GitHub: https://github.com/{GITHUB_REPO}")
        return

    clipper = WebClipper(
        vault_path=args.vault,
        base_dir=args.base_dir,
        download_images=not args.no_images,
        rate_limit=args.rate,
    )

    # 扫描 Vault 模式
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

    # 更新 MOC 模式
    if args.update_moc:
        moc_path = WebClipper.update_moc(
            vault_path=args.vault or clipper.vault_path,
            base_dir=args.base_dir or DEFAULT_BASE_DIR,
            moc_name=args.moc_name,
        )
        print(f"MOC 更新完成: {moc_path}")
        return

    # 批量模式（JSON 文件）
    if args.batch:
        with open(args.batch, 'r', encoding='utf-8') as f:
            articles = json.load(f)
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

    # URL 列表文件模式（v3.2 兼容）
    if args.url_file:
        with open(args.url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f
                    if line.strip() and not line.strip().startswith('#')]
        print(f"批量剪藏 {len(urls)} 篇文章...")
        articles = [{"url": u} for u in urls]
        results = clipper.clip_batch(articles, dedup=not args.no_dedup)
        ok = sum(1 for r in results if r.get("success"))
        fail = len(results) - ok
        print(f"\n批量完成: {ok} 成功, {fail} 失败")
        for r in results:
            if r.get("success"):
                print(f"  ✓ {r['title'][:40]}...")
            else:
                print(f"  ✗ 失败: {r.get('error', '未知错误')[:60]}")
        return

    # 单篇模式
    if args.url:
        result = clipper.clip_url(args.url, title=args.title or None,
                                  category=args.category, account=args.account)
        if result["success"]:
            print(f"✓ 剪藏成功: {result['file_path']}")
            print(f"  标题: {result['title']}")
            print(f"  作者: {result.get('author', '')}")
            print(f"  公众号: {result.get('account', '')}")
            print(f"  发布日期: {result.get('publish_date', '')}")
            print(f"  内容: {result['content_length']} 字符")
            print(f"  图片: {result['image_downloaded']}/{result['image_total']} 下载成功")
            if result['image_failed']:
                print(f"  失败图片: {result['image_failed']} 张")
            print(f"  抓取方式: {result['fetch_method']}")
        else:
            print(f"✗ 剪藏失败: {result['error']}")
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
