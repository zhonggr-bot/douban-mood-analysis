# -*- coding: utf-8 -*-
"""
影评分析：词云 + 情感分析
==========================
输入：crawler.py 生成的 comments.json
输出：wordcloud.png（词云）、sentiment.png（情感分布饼图）、终端打印统计
"""
import json
from collections import Counter

import jieba
import matplotlib
matplotlib.use("Agg")          # 无界面环境也能出图
import matplotlib.pyplot as plt
from snownlp import SnowNLP
from wordcloud import WordCloud

# Windows 中文字体（不指定则汉字变方块）
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"

# 常用停用词（的/了/是 等无意义虚词 + 影评高频口水词）
STOPWORDS = {
    "的", "了", "是", "在", "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "这", "那", "有", "就", "都", "也", "和", "与", "或", "而", "但", "不", "没",
    "没有", "一个", "一部", "什么", "怎么", "这样", "那样", "这个", "那个", "之",
    "着", "过", "得", "地", "啊", "吧", "呢", "吗", "嘛", "么", "很", "太", "最",
    "更", "还", "又", "再", "被", "把", "让", "给", "对", "从", "向", "到", "于",
    "电影", "影片", "这部", "看", "感觉", "真的", "就是", "不是", "还是",
}


def load_comments():
    with open("comments.json", encoding="utf-8") as f:
        return json.load(f)


def make_wordcloud(comments):
    words = []
    for c in comments:
        for w in jieba.lcut(c["content"]):
            w = w.strip()
            if len(w) >= 2 and w not in STOPWORDS and not w.isascii():
                words.append(w)
    counter = Counter(words)
    print("高频词 TOP 15:", counter.most_common(15))

    wc = WordCloud(font_path=FONT_PATH, width=900, height=600,
                   background_color="white", max_words=150)
    wc.generate_from_frequencies(counter)
    wc.to_file("wordcloud.png")
    print("词云已保存 -> wordcloud.png")


def sentiment_analysis(comments):
    pos, neu, neg = 0, 0, 0
    for c in comments:
        score = SnowNLP(c["content"]).sentiments   # 0~1，越接近 1 越正面
        if score > 0.6:
            pos += 1
        elif score < 0.4:
            neg += 1
        else:
            neu += 1

    total = len(comments)
    print(f"情感分析：正面 {pos}（{pos / total:.1%}） "
          f"中性 {neu}（{neu / total:.1%}） 负面 {neg}（{neg / total:.1%}）")

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]   # 饼图中文
    plt.rcParams["axes.unicode_minus"] = False
    plt.figure(figsize=(6, 6))
    plt.pie([pos, neu, neg],
            labels=[f"正面 {pos}", f"中性 {neu}", f"负面 {neg}"],
            autopct="%.1f%%", colors=["#4CAF50", "#9E9E9E", "#F44336"])
    plt.title(f"《肖申克的救赎》短评情感分布（n={total}）")
    plt.savefig("sentiment.png", dpi=150, bbox_inches="tight")
    print("情感分布图已保存 -> sentiment.png")


def main():
    comments = load_comments()
    print(f"共加载 {len(comments)} 条评论")
    make_wordcloud(comments)
    sentiment_analysis(comments)


if __name__ == "__main__":
    main()
