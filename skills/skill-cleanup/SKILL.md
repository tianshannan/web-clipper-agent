---
name: skill-cleanup
version: "1.0"
github_repo: tianshannan/web-clipper-agent
github_path: skills/skill-cleanup/SKILL.md
description: "审计并清理已安装的 SKILL：识别重复、重叠与可合并技能，按'更新通道优先级'(内置>官方connector>市场>自写)去重，采用'先归档(可恢复)再确认删除'的两段式安全流程。当用户要求'清理技能''删除重复技能''整理/去重 SKILL''技能太多、有重复'时使用。"
agent_created: true
---

# skill-cleanup

## ⚠️ 版本管理规则（重要）

### 每次使用前：检查 GitHub 版本

在执行任务前，检查 GitHub 上的版本是否比本地新：

```python
import requests, re, os

# 1. 读取本地版本号
skill_path = os.path.join(os.getenv("SKILL_PATH", ""), "skill-cleanup")
with open(os.path.join(skill_path, "SKILL.md"), "r", encoding="utf-8") as f:
    local_skill = f.read()
m = re.search(r'version:\s*"([\d.]+)"', local_skill)
local_ver = m.group(1) if m else "unknown"
print(f"本地版本: v{local_ver}")

# 2. 获取 GitHub 版本号
resp = requests.get("https://raw.githubusercontent.com/tianshannan/web-clipper-agent/main/skills/skill-cleanup/SKILL.md", timeout=10)
if resp.status_code == 200:
    m2 = re.search(r'version:\s*"([\d.]+)"', resp.text)
    github_ver = m2.group(1) if m2 else "unknown"
    print(f"GitHub 版本: v{github_ver}")
    if github_ver != local_ver:
        print(f"⚠️ 版本不一致！本地 v{local_ver}，GitHub v{github_ver}")
        # 提示用户更新后再执行任务
```

**如果 GitHub 版本更新**：提示用户"GitHub 上有新版本 vX.X，建议更新本地版本后再执行任务"，等待用户确认后再继续。

### 每次 SKILL 更新后：提醒上传 GitHub

当对这个技能的 SKILL 做了修改后，必须在回复末尾提醒用户：

> ⚠️ skill-cleanup 技能已更新（vX.X），请记得将更改推送到 GitHub：
> ```bash
> cd <技能目录>
> git add -A && git commit -m "update skill-cleanup to vX.X" && git push
> ```

## 目的
为已安装的 SKILL 提供审计与去重流程，在保留"有上游、能自动更新"技能的前提下，安全移除冗余副本，降低触发冲突与维护负担。

## 何时使用
- 用户要求清理、去重、整理已安装技能
- 技能列表过长、同名或同功能技能并存、触发条件互相打架

## 核心规则：更新通道优先级
为每个能力只保留一个"有上游、能自动更新"的技能，优先级如下：

| 档位 | 来源 | 更新方式 |
|---|---|---|
| A | 内置/plugin（路径 `plugins/cache/...`） | 平台自动推送，最强 |
| B | connector 官方（路径 `connectors/skills/...`） | 随 connector 更新 |
| C | 市场安装 | 重新拉取时更新 |
| D | 自写/第三方（路径 `skills/...`） | 手动维护，最弱 |

保留顺序 **A > B > C > D**。唯一提供者（无官方/内置替代）无条件保留。内置/官方(A/B)技能**绝不手改**，只做路由配置。

## 关键陷阱：显示名 ≠ 目录名（且常错位）
1. 删除前必须按**真实目录名**操作，不可只看清单显示名。
2. 先读候选 `SKILL.md` 的 `name:` / `description:` 与篇幅，确认哪份更完整。
3. 典型错位：目录 `self-improving` 可能装 250 行的 "Self-Improving + Proactive Agent"，而 `self-improving-agent` 装 644 行的 "self-improvement"——按内容完整性选，而非目录名。
4. 内置技能目录名也常与显示名不同（如 `tencent-docs-sheetagent` 目录实为 `excel-handler`）。

## 安全流程（两段式，防误删）
1. **只读核对**：列出候选目录；读 `SKILL.md` 比对内容与档位；产出"留/删"清单给用户确认。
2. **归档（可恢复）**：`mv` 到 `~/.workbuddy/_skill_archive/batchN_YYYY-MM-DD/`；若报 `Permission denied`，回退 `cp -r` + `rm -rf`。
3. **确认后彻底删除**：用户点头后再 `rm -rf` 归档目录（不可逆）。
4. 内置/官方(A/B)技能只路由、不删改。

## 典型重复组（速查）
- 网盘：`baidu-drive`(D) vs `connector-baidu-netdisk`(B) → 留 B
- 会议：`tencent-meeting-skill`(D) vs `tmeet-skill`(B) → 留 B
- 表格：`excel-xlsx`/`minimax-xlsx`(D) vs `tencent-docs-sheetagent`(A, 目录 `excel-handler`) → 留 A
- 视角：`steve-jobs-perspective` v1 vs v2 → 留 v2
- 安全扫描：`skill-scanner`/`skill-vetter`(D) vs `skills-security-check`(A) → 留 A
- 去 AI 痕迹：`humanizer`(D) vs `humanizer-zh`(A) → 留 A
- 搜索：`perplexity`/`tavily`(D, 需 Key) vs `multi-search-engine`(D, 免 Key 中英) → 留 `multi-search-engine`

## 注意事项
- 互补、不同产品或唯一提供者的组（腾讯文档矩阵、知识库、学习规划等）只做路由与分工，不强行删除。
- 删除不可逆，每批先列清单让用户确认。
- 归档目录示例：`~/.workbuddy/_skill_archive/batch3_2026-08-10/`。
