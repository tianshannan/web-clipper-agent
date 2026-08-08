# 微信公众号文章解析参考

## 微信文章 HTML 结构

```
#activity-name        → 标题
#js_name              → 公众号名称
#publish_time         → 发布时间
meta[og:description]  → 摘要
#js_content           → 正文容器（visibility:hidden 预渲染，需保留）
```

## 图片 data-src 陷阱（最重要）

微信公众号图片用 `data-src` 属性而非标准 `src`。BeautifulSoup 的 `img.get("src")` 返回空，markdownify 转换后产生 `![]()` 空图片标签。

**解决方案**：在 markdownify 转换前，遍历所有 `<img>` 标签，将 `data-src` 值复制到 `src` 属性。

```python
for img in soup.find_all("img"):
    data_src = img.get("data-src", "")
    if data_src and not img.get("src"):
        img["src"] = data_src
```

## 微信特有 HTML 问题

### 1. 粗体内部 `<br>` 撕裂

微信高频 bug：`<strong>` 包裹整段文字，内部嵌入 `<br>` 分行。markdownify 转换后 `**` 标记被段落分隔撕成两半。

**修复**：转换前将 `<strong>/<b>/<em>/<i>` 内的 `<br>` 替换为空格。

### 2. 标题内 `<br>` 产生非法多行标题

`<h1-6>` 标签内的 `<br>` 导致 markdownify 生成多行标题。

**修复**：转换前将 heading 内的 `<br>` 压缩为空格。

### 3. `***text***` 三星号加粗

微信用 `***text***` 表示加粗段落标题，markdownify 原样保留。

**修复**：正则替换 `***` → `**`。

### 4. 行内 `###` 误转

markdownify 可能将 `<strong>` 误转为行内 `###text###`。

**修复**：正则替换 `###(.+?)###` → `**\1**`。

### 5. 未闭合 `**`

每行 `**` 数量为奇数时行尾补 `**`，防止后续文本被误加粗。

### 6. `\x0d\x0a` 转义字符

部分 IMA 剪藏的文章正文和摘要中包含 `\x0d\x0a`（即 `\r\n` 的字面量形式），需替换为 `\n`。

### 7. HTML 数字实体

`&#NN;`（十进制）和 `&#xNN;`（十六进制）需解码为对应字符。常见命名实体：`&nbsp;` `&amp;` `&lt;` `&gt;` `&quot;` `&apos`。

## 微信正文 #标签污染

公众号文章文末常自带 `#话题标签`（如 `#科研伦理 #免费下载`），Obsidian 会将其识别为笔记标签，污染 P.A.I.R v5 标签体系。

**清理规则**：
1. 分割 frontmatter 和 body（`---` 分隔），**只清理 body**
2. 删除整行只含 `#标签` 的行（微信文末话题标签行）
3. 删除行内嵌入的 `#标签`（如 `#Excel模板 #CRA工具` → `Excel模板 CRA工具`）
4. 判断标准：`#` 后无空格（非 Markdown 标题 `# 标题`），标签名 2-15 个中文字符/字母

## display:none vs visibility:hidden

微信 `#js_content` 正文容器常设为 `visibility:hidden`（预渲染防闪烁）。必须保留此元素，只过滤 `display:none` 的元素。

```python
# 正确：只移除 display:none
if "display:none" in style.replace(" ", ""):
    el.decompose()
# 错误：会误删正文
if "hidden" in style:
    el.decompose()
```

## 失效页面检测

抓取后检查以下关键词，命中则报错终止，不产出垃圾文件：

- `已被发布者删除`
- `违规无法查看`
- `当前环境异常`
- `完成验证后即可继续访问`
- `公众号已迁移`
- `账号已注销`

## 图片防盗链

微信图片有 Referer 防盗链。下载时必须带 `Referer: https://mp.weixin.qq.com/`，否则返回 403。

## 摘要回退

无 `og:description` 时取正文首个有效段落（≥20字）：
- 跳过 `#`/`!`/`---` 开头的行
- 跳过推广段（往期精彩/扫码关注/点击下方/推荐阅读/更多精彩）
- 跳过纯图片行 `![](url)` 和 `![[img.jpg]]`
- 截断 200 字
