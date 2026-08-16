# IMA 知识库剪藏参考

## IMA 技能路径

- 技能名：`ima-skill`
- 位置：`target_skills/ima-skill`
- 凭证：`~/.config/ima/client_id` 和 `~/.config/ima/api_key`

## 常用 IMA API 调用

### 搜索知识库
```bash
node "$SKILL_DIR/ima_api.cjs" "openapi/wiki/v1/search_knowledge_base" '{"query":"关键词","cursor":"","limit":20}' "$OPTS"
```

### 搜索知识库内容
```bash
node "$SKILL_DIR/ima_api.cjs" "openapi/wiki/v1/search_knowledge" '{"query":"关键词","knowledge_base_id":"<kb_id>","cursor":""}' "$OPTS"
```

### 浏览文件夹内容
```bash
node "$SKILL_DIR/ima_api.cjs" "openapi/wiki/v1/get_knowledge_list" '{"knowledge_base_id":"<kb_id>","folder_id":"<folder_id>","cursor":"","limit":50}' "$OPTS"
```

### 获取文章真实链接
```bash
node "$SKILL_DIR/ima_api.cjs" "openapi/wiki/v1/get_media_info" '{"media_id":"<media_id>"}' "$OPTS"
```
从返回的 `data.url_info.url` 获取真实微信链接。

## 小虎的 IMA 知识库

| 知识库 | kb_id |
|--------|-------|
| 小虎同学的CRA日记 | `8vkP4IGjqYEHOW5tqlq0DrHOFZqTas5GOL7O6_Q2GR0=` |

### 公众号文件夹

- folder_id: `folder_7459445671998503`
- 包含 39 个公众号子文件夹
- 每个子文件夹包含 40-50 篇微信文章

## media_type 对照

| media_type | 含义 |
|-----------|------|
| 1 | PDF 文件 |
| 4 | PPT 文件 |
| 5 | Excel 文件 |
| 6 | 微信文章（可剪藏） |
| 9 | 图片 |
| 11 | 笔记 |
| 99 | 文件夹 |
