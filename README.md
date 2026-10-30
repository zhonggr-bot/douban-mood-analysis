# 豆瓣电影影评爬取与情感分析

对豆瓣电影《肖申克的救赎》短评进行爬取、存储与可视化分析。

## 功能

- `crawler.py`：爬取短评（用户名 / 星级 / 正文 / 时间 / 有用数），落盘 `comments.json` 并写入 MySQL（内容 MD5 去重，重复运行安全）
- `analyze.py`：读取 `comments.json`，生成词云 `wordcloud.png` 与情感分布饼图 `sentiment.png`

## 运行

```bash
pip install -r requirements.txt

# 豆瓣短评页需要登录 Cookie：浏览器登录豆瓣后，F12 -> Network ->
# 任选一请求 -> Request Headers -> 复制 Cookie 整段值
$env:DOUBAN_COOKIE = "你的Cookie"      # PowerShell
python crawler.py

python analyze.py
```

## 反爬应对说明

- UA 伪装 + Referer 头 + 每页限速 5 秒
- 检测验证页（`form#sec`）与 403 登录拦截，遇到即停止并提示
- 未登录时豆瓣仅开放前若干页短评（约 6 页 / 120 条），登录后可爬取更多

## 输出示例

| 文件 | 内容 |
|---|---|
| `comments.json` | 结构化评论数据 |
| `wordcloud.png` | 高频词词云（jieba 分词 + 停用词过滤） |
| `sentiment.png` | SnowNLP 情感分布（正面 / 中性 / 负面） |
