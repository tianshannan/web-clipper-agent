---
name: clinical-trial-crc-visit
version: "1.0"
github_repo: tianshannan/web-clipper-agent
github_path: skills/clinical-trial-crc-visit/SKILL.md
description: 临床试验 CRC（研究协调员）视角的访视安排与注意事项技能。当用户需要为 CRC 生成研究者访视检查清单、各访视必做/可选项目与时间窗、眼科（nAMD/抗VEGF）等专科试验注意事项、常见错误与预防速查表，或把多份方案/培训资料整合为结构化 Word 交付文档时使用。覆盖访视时间轴编排、给药频率调整（T&E）逻辑、眼科检查规范、IVT 注射、文档自动化生成（python-docx）。
---

# 临床试验 CRC 访视安排及注意事项

## ⚠️ 版本管理规则（重要）

### 每次使用前：检查 GitHub 版本

在执行任务前，检查 GitHub 上的版本是否比本地新：

```python
import requests, re, os

# 1. 读取本地版本号（从 SKILL.md frontmatter 的 version 字段）
skill_path = os.path.join(os.getenv("SKILL_PATH", ""), "clinical-trial-crc-visit")
with open(os.path.join(skill_path, "SKILL.md"), "r", encoding="utf-8") as f:
    local_skill = f.read()
m = re.search(r'version:\s*"([\d.]+)"', local_skill)
local_ver = m.group(1) if m else "unknown"
print(f"本地版本: v{local_ver}")

# 2. 获取 GitHub 版本号
resp = requests.get("https://raw.githubusercontent.com/tianshannan/web-clipper-agent/main/skills/clinical-trial-crc-visit/SKILL.md", timeout=10)
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

当对这个技能的 SKILL.md 做了修改后，必须在回复末尾提醒用户：

> ⚠️ clinical-trial-crc-visit 技能已更新（vX.X），请记得将更改推送到 GitHub：
> ```bash
> cd <技能目录>
> git add -A && git commit -m "update clinical-trial-crc-visit to vX.X" && git push
> ```

为 CRC（临床研究协调员）视角的临床试验访视安排与注意事项提供可复用的方法论与文档生成模板。本技能以 QL1207H-301（nAMD 玻璃体内注射 III 期）项目为范例，但逻辑可移植到其他眼科及常规临床试验。

## 一、CRC 访视安排核心逻辑

### 1.1 时间轴与访视编号
- 按**研究周（W）**对应**研究日（D）**编排：W0/D1 = 首次给药日，之后每 4 周为一节点（W4/D29、W8/D57…）。
- 访视编号 V1→Vn 与周次对应；**关键评估时点须独立成访视**（如给药频率调整评估点 W36，无论是否给药都必须完成评估，不得埋在"V9–V12 第28–40周"这类合并节中）。
- 时间窗：治疗期访视统一 `±5 天`；筛选期/基线无时间窗（须在 D1 前完成）；采血/影像有各自更窄窗（如免疫原性 ±3d、±7d）。

### 1.2 必做 / 可选 / 时间窗 三层结构
每个访视的检查项按三类标注，便于 CRC 快速核对：
- **必做**：每次必查（如 BCVA、IOP、裂隙灯、间接检眼镜、OCT 研究眼、安全性评估、日记卡）
- **可选 / 条件**：仅特定访视或满足条件才做（如 FFA/FP 仅当 BCVA 较基线下降 >5 字母时加做；妊娠仅 WOCBP 且特定周次）
- **给药（视情况）**：根据给药频率调整结果决定
- **采血**：PK（仅约 60 例 PK 参与者）/ 免疫原性（所有参与者），注意采样时间窗（-3~0h 给药前、给药后 24h±2h）

### 1.3 给药频率调整（T&E，治疗—延长）逻辑（以本项目为例）
- 负荷期固定：W0、W4、W8 每 4 周 1 次（连续 3 针）；W12 不给药（主要疗效终点 + 全套检查）。
- W16 起进入调整：评估时点固定 **W16 / W20 / W24 / W36**（共 4 个），以 **W12** 为基准。
- 调整标准（须**同时满足**两条）：① BCVA 较 W12 下降 >5 个字母；② CRT 较 W12 增加 >25μm 或新发中心凹出血/新发 PCV。
- 路径：W16→Q8W / W20→Q8W / W24→Q12W（W36 可进一步由 Q12 缩短为 Q8）。
- W12 不可用时按 W8→W4 顺序替代；W28/W32 非评估时点，按当前所处行维持频率。
- 调药访视操作：提前 1 天联系影像 + PM；系统上传勾选"加急"并备注；不需做的影像点"miss"并注明。

## 二、眼科临床试验专项注意事项（可移植）

### 2.1 BCVA / ETDRS 视力
- 散瞳前检查；首字母正确读出 ≥4 才进下一行；某行未读出记"0"（勿用双竖线划掉）。
- 4 米处正确字母 <20 个须到 1 米检查并记录；>20 个仍做 1 米属多余。
- 视力得分 = 4米字母数 + (4米≥20记30否则00) + 1米字母数。
- 给药前 BCVA 波动尽量 <5 字母（V1→V2 仅隔数天）。

### 2.2 眼压（IOP）
- 正常 10–21 mmHg；给药前测双眼，给药后 30–60 min 仅测研究眼。
- 给药后较给药前升高 >10 mmHg → 约 30 min 复测；以**复测值（离开中心前最后一次）**判 AE。
- >36 mmHg 用 Goldmann/Tonopen/ICare 复测；同一受试者全程同一类型眼压计。
- NCS（非并发症）：一过性、当天恢复、无症状、无需治疗、单纯 ≤30 mmHg、较注射前 <8 mmHg、无视野损害。≥8 mmHg 或 >30 mmHg 且无解释须记 AE（参 CTCAE 5.0，需治疗 ≥2 级）。

### 2.3 裂隙灯（眼前节）vs 间接检眼镜（眼后节）
- 裂隙灯：角膜/前房/虹膜/瞳孔/晶状体（C/N/P 评级）/玻璃体；看不到黄斑。
- 间接检眼镜：玻璃体/视盘/黄斑/视网膜；nAMD 眼底发现填此处。
- **严禁前后节填反、左右眼填反**；眼前节异常（如晶状体混浊）不应勾选为"研究疾病"。

### 2.4 OCT / FFA / FP
- OCT：筛选期/D1/W12/W24/W48 双眼，其余仅研究眼；CRT = ILM–RPE 平均厚度（不含 PED）；同中心同设备边界定义与人工校准须前后一致；IRF/SRF 须明确"有/无"，勿仅写"正常"。
- FFA 仅注射一次荧光素造影剂；FP/FFA 计划检查在筛选期/W12/W24/W48；W16/W20/W36 仅当 BCVA 降 >5 字母加做；图像传独立读片中心，照相师须认证。

### 2.5 IVT 玻璃体内注射
- 术前：表面麻醉、眼睑消毒、刷手戴无菌手套、开睑器、5% 聚维酮碘结膜囊消毒 ≥30s、18G 抽药换 30G 调 0.07ml。
- 注射：角巩膜缘后 3.5–4.0mm（有晶体眼 4mm / 人工晶体眼 3.5mm），垂直进针注 0.07ml(8mg)，拔针轻压防反流。
- 术后：酌情抗生素滴眼液 3 天；给药后 30 min 测 IOP；第 3±1 天电话随访（记录表+病历+通话截图）。

## 三、CRC 常见错误与预防（速查）

| 易错环节 | 正确做法 |
|---------|---------|
| BCVA 某行未读出 | 记"0"，勿双竖线划掉 |
| 四米处字母 <20 | 到 1 米处检查并记录 |
| 给药后 IOP 测哪眼 | 仅研究眼（给药前才测双眼） |
| IOP 升高 >给药前 10 mmHg | 约 30 min 复测，以复测值判 AE |
| 眼底发现填单 | 眼后节→间接检眼镜；眼前节→裂隙灯 |
| OCT CRT 边界 | 统一 ILM–RPE，人工校准，前后一致 |
| IRF/SRF 记录 | 明确"有/无"，勿仅写"正常" |
| 调药访视影像上传 | 提前联系；勾选加急并备注；不做的 miss 掉 |
| 生命体征/采血顺序 | 生命体征在采血前、给药前完成；实验室样本在 FFA 前 |
| 生物样本离心温度 | 记实际设定温度，非范围 |
| 给药后第 3 天 | 电话随访 + 记录表 + 病历 + 通话截图 |
| 仅授权不操作 | 不合规；须实际操作人员才授权 |

## 四、文档生成工作流（python-docx）

当用户要求生成/重制访视清单或注意事项汇编 Word 时：

1. **检索资料**：从 IMA「陈虎的知识库」（KB `0019d0ff28400327`，ima-mcp）按 folder 拉取方案与培训原文：
   - 项目组培训 `folder_7482804329790257`（方案1.1/质量培训/医学培训）
   - 方案1.0培训 `folder_7482804333995649`（眼球结构/IVT/OCT/FFA/FP）
   - 项目质量培训 `folder_7482804333984100`（BCVA/IOP/AE/授权/ISF）
   - 链路：`get_knowledge_base_list` → `get_knowledge_list` → `search_knowledge`（直接传 `{"knowledge_base_id":"...","query":"..."}`，勿嵌套数组）→ `fetch_media_content`
2. **梳理结构**：任务一按 V1→Vn 排必做/可选/时间窗；任务二按「眼科检查规范 → IVT → 常见错误与预防 → 易错点速查表 → 授权 → ISF → 重要提醒」组织。
3. **生成**（python-docx，置于隔离 venv，pip 用清华镜像 `https://pypi.tuna.tsinghua.edu.cn/simple` 防 lxml 超时）：
   - 表格 `Light Grid Accent 1`；单元格配色：必做 `E8F0FE` / 给药 `FFF3E0` / 采血 `F3E5F5`
   - 标题黑体，层级配色 `#1F4768` / `#2E5C8A` / `#3A6EA5`
   - 关键提示用 `⚠` 红色加粗
4. **用户更正处理**：用户常以**黄色高亮**标注重点 + 直接文字修订（**无 Word 批注**）。重制时须：①保留高亮要点落到正文 ②修正编号重复 ③拆分关键评估访视为独立访视（如 W36）④整合多份同源文档互补不丢内容。
5. **校验**：生成后回读（遍历 paragraph/table，抓取 `w:highlight` 与 `w:commentReference`）确认结构/编号/表格正确再交付。

## 五、使用提示
- 本技能偏 CRC/文档生成视角；涉及法规判定（GCP 条款、AE 上报时限、国家局核查）请配合 `gcp-compliance` 或「临床试验高级监查员」专家。
- 药物安全性判断以项目医学监查员（MM）意见为准；不替用户做最终决策。
- 方案更新或项目组通知以最新要求为准。
