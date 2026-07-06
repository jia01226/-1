"""枕边日记 · 夜班小工人：
   每晚回顾当天的对话 → 替角色写一篇睡前日记 → 存进日记本（用户想看就翻）。
   由 cron 定时调用（建议 23:30）：  ./venv/bin/python diary_writer.py
   crontab 示例：  30 23 * * *  cd /path/to/platform && ./venv/bin/python diary_writer.py
"""
import os

# --- 先加载 .env（cron 不会自动加载，所以自己读；跟 proactive.py 一个路数）---
def _load_env():
    p = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

import datetime
import db, chat_ai

def china_today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date().isoformat()

if __name__ == "__main__":
    db.init_db()
    today = china_today()
    if db.diary_written_today(today):
        print(f"[{today}] 今天已经写过日记，跳过")
    else:
        entry = chat_ai.write_diary(today)
        if entry:
            did = db.add_diary(entry["title"], entry["content"], entry["mood"], entry["locked"])
            lock = "🔒" if entry["locked"] else ""
            print(f"[{today}] 日记已写好 #{did} {lock}「{entry['title']}」({entry['mood']})")
        else:
            print(f"[{today}] 今天没聊过天（或生成失败），不写")
