# -*- coding: utf-8 -*-
"""
豆瓣电影短评爬虫
================
目标：《肖申克的救赎》短评页，翻页爬取用户名 / 星级 / 正文 / 时间 / 有用数，
落盘 comments.json，并写入 MySQL（表 comments，内容 MD5 去重，重复运行不重复插入）。

登录 Cookie 通过环境变量 DOUBAN_COOKIE 传入，绝不硬编码：
    PowerShell:  $env:DOUBAN_COOKIE = "你的Cookie整段值"
"""
import hashlib
import json
import os
import time

import pymysql
import requests
from bs4 import BeautifulSoup

# ---------- 配置 ----------
MOVIE_ID = "1292052"          # 肖申克的救赎
MOVIE_NAME = "肖申克的救赎"
MAX_PAGES = 6                 # 未登录上限约 6 页（120 条）；登录后可调大
SLEEP_SECONDS = 5             # 每页限速，避免触发反爬

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": os.environ.get("DOUBAN_COOKIE", ""),
    "Referer": f"https://movie.douban.com/subject/{MOVIE_ID}/",
}

DB = dict(host="localhost", port=3306, user="root", password="123456",
          database="douban_mood", charset="utf8mb4")

JSON_FILE = "comments.json"


def parse_page(html):
    """解析一页短评，返回评论字典列表；被反爬拦截时返回 None"""
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("form", id="sec"):
        return None  # 触发算力验证页
    items = soup.find_all("div", class_="comment-item")
    result = []
    for item in items:
        user = item.select_one(".comment-info a")
        star = item.find("span", class_="rating")
        short = item.find("span", class_="short")
        ctime = item.find("span", class_="comment-time")
        votes = item.find("span", class_="votes")
        content = short.get_text(strip=True) if short else ""
        if not content:
            continue
        result.append({
            "movie": MOVIE_NAME,
            "username": user.get_text(strip=True) if user else "",
            # 星级藏在 class 名里：allstar50 -> 5 星；未打分则为 None
            "rating": int(star["class"][0].replace("allstar", "")) // 10 if star else None,
            "content": content,
            "comment_time": ctime.get("title", "").strip() if ctime else "",
            "votes": int(votes.get_text(strip=True)) if votes and votes.get_text(strip=True).isdigit() else 0,
        })
    return result


def init_db():
    """建库建表，返回连接"""
    # DB 里已含 charset，只需剔除 database（建库前不能带库名）
    conn = pymysql.connect(**{k: v for k, v in DB.items() if k != "database"})
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE IF NOT EXISTS douban_mood DEFAULT CHARSET utf8mb4")
    conn.close()

    conn = pymysql.connect(**DB)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                movie VARCHAR(64) NOT NULL,
                username VARCHAR(128) NOT NULL,
                rating TINYINT NULL,
                content TEXT NOT NULL,
                comment_time VARCHAR(32) DEFAULT '',
                votes INT DEFAULT 0,
                content_md5 CHAR(32) NOT NULL,
                UNIQUE KEY uk_md5 (content_md5)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    conn.commit()
    return conn


def save_to_mysql(conn, comments):
    """INSERT IGNORE：靠 content_md5 唯一索引去重，重复运行安全"""
    sql = ("INSERT IGNORE INTO comments "
           "(movie, username, rating, content, comment_time, votes, content_md5) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s)")
    rows = [(
        c["movie"], c["username"], c["rating"], c["content"], c["comment_time"],
        c["votes"], hashlib.md5(c["content"].encode("utf-8")).hexdigest(),
    ) for c in comments]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM comments")
        before = cur.fetchone()[0]
        cur.executemany(sql, rows)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM comments")
        after = cur.fetchone()[0]
    return after - before


def main():
    all_comments = []
    for page in range(MAX_PAGES):
        start = page * 20
        url = (f"https://movie.douban.com/subject/{MOVIE_ID}/comments"
               f"?start={start}&limit=20&status=P&sort=new_score")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 403:
            print(f"[第{page + 1}页] 403 需要登录：请设置环境变量 DOUBAN_COOKIE 后重试")
            break
        resp.raise_for_status()

        parsed = parse_page(resp.text)
        if parsed is None:
            print(f"[第{page + 1}页] 触发反爬验证页：请求太频繁，等 30 分钟再试")
            break
        if not parsed:
            print(f"[第{page + 1}页] 无数据，到达翻页上限")
            break

        all_comments.extend(parsed)
        print(f"[第{page + 1}页] 本页 {len(parsed)} 条，累计 {len(all_comments)} 条")
        time.sleep(SLEEP_SECONDS)

    if not all_comments:
        print("没有爬到任何数据")
        return

    # 1) 落盘 JSON（数据先于数据库，避免反复爬）
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(all_comments)} 条到 {JSON_FILE}")

    # 2) 写入 MySQL
    conn = init_db()
    inserted = save_to_mysql(conn, all_comments)
    conn.close()
    print(f"MySQL 新增 {inserted} 条（重复内容自动忽略）")


if __name__ == "__main__":
    main()
