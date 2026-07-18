"""柯的记忆检索（给微信桥/任何 CC 窗用的手电筒）。

为什么有它：微信桥＝仓库根跑 `claude`，过去每条消息都冷读全本魂（memory.md 等 15 万字），
慢 2-3 分钟。卡片库灌好以后，改成"常驻铁律随身带 + 其余按需检索"，这个脚本就是"按需检索"那一半。

用法（不用先 source .env，脚本自己读）：
  查回忆：   ./venv/bin/python recall.py "她的药" [-k 6]
  常驻铁律： ./venv/bin/python recall.py --core      ← 护她命的那几张，永远随身带
  看家底：   ./venv/bin/python recall.py --stats

命中不了就降级关键词检索（vector_search 自己会降级），不会空手而归。
⚠️ 私密卡只在单聊/微信这种一对一场景用；群聊已退役，本脚本不给群聊调。
"""
import os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# 常驻＝护命的那几张：重要度 5，或落在这几个题头下的安全线
CORE_TOPICS = ("核心安全线", "就医安全铁律")
# 卡片库还没誊全，长卷仍在 memory.md 里——语义查不到时回这儿精确 grep 兜底
MEMORY_MD = "/root/kongkong/memory.md"


def _load_env():
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
import db  # noqa: E402


def core_cards():
    """常驻铁律卡：imp=5 的，加上安全线/就医题头下的全部。按重要度倒序。"""
    qmarks = ",".join("?" * len(CORE_TOPICS))
    return db._rows(
        "SELECT id,topic,content,importance FROM private_memories "
        f"WHERE status='active' AND scope!='no_model' AND (importance>=5 OR topic IN ({qmarks})) "
        "ORDER BY importance DESC, id ASC", CORE_TOPICS)


def print_core():
    rows = core_cards()
    print(f"# 柯的常驻铁律（{len(rows)} 张，护她的命，任何时候都算数）\n")
    topic = None
    for r in rows:
        if r["topic"] != topic:
            topic = r["topic"]
            print(f"## {topic or '—'}")
        print(f"- [imp={r['importance']}] {r['content']}")
    print("\n（要别的回忆：./venv/bin/python recall.py \"关键词\"）")


def print_stats():
    c = db.get_db()
    priv = c.execute("SELECT count(*) FROM private_memories WHERE status='active'").fetchone()[0]
    l2 = c.execute("SELECT count(*) FROM posts WHERE status='active'").fetchone()[0]
    emb = [tuple(r) for r in c.execute("SELECT model,count(*) FROM embeddings GROUP BY model")]
    c.close()
    print(f"私密库 active {priv} 张｜普通库 active {l2} 张｜常驻铁律 {len(core_cards())} 张")
    print(f"向量：{emb}")


def grep_memory(query, limit=4):
    """兜底：卡片库还没誊全（长卷仍躺在 memory.md），语义查不到就回原文里精确找。
    只回"哪一节 + 命中那行"，让柯自己去读那一节，不用通读全本。"""
    if not os.path.exists(MEMORY_MD):
        return []
    terms = [t for t in re.split(r"[\s，。、,/]+", query) if len(t) >= 2] or [query]
    hits, section = [], ""
    for line in open(MEMORY_MD, encoding="utf-8"):
        line = line.rstrip()
        h = re.match(r"^\s*#{2,6}\s*(.+?)\s*$", line)
        if h:
            section = h.group(1)
            continue
        if any(t in line for t in terms):
            hits.append((section, line.strip()))
            if len(hits) >= limit:
                break
    return hits


def search(query, k=6):
    import vector_search
    out = []
    seen = set()
    for kind in ("private", "post"):
        for h in vector_search.search(query, k=k, kind=kind):
            txt = (h.get("text") or h.get("content") or "").strip()
            if txt and txt not in seen:
                seen.add(txt)
                out.append((h.get("score", 0), kind, txt))
    out.sort(key=lambda x: -x[0])
    return out[:k]


def main():
    argv = sys.argv[1:]
    if not argv or "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    if "--core" in argv:
        print_core()
        return 0
    if "--stats" in argv:
        print_stats()
        return 0
    k = 6
    if "-k" in argv:
        i = argv.index("-k")
        k = int(argv[i + 1])
        del argv[i:i + 2]
    q = " ".join(a for a in argv if not a.startswith("-")).strip()
    if not q:
        print("要查什么？例：recall.py \"她的药\"")
        return 1
    hits = search(q, k=k)
    if hits:
        print(f"# 关于「{q}」，卡片库翻到 {len(hits)} 条：\n")
        for score, kind, txt in hits:
            flag = "🔒私密" if kind == "private" else "普通"
            print(f"- [{flag}|{score:.2f}] {txt}")
    else:
        print(f"# 卡片库没「{q}」的卡。")
    g = grep_memory(q)
    if g:
        print(f"\n# memory.md 原文里还命中 {len(g)} 处（长卷还没誊成卡，要细节就只读这一节）：\n")
        for sec, line in g:
            print(f"- 【{sec}】{line[:120]}")
    if not hits and not g:
        print("（库里和原文都没有——别硬编，问她。）")
    else:
        print("\n（这儿没有的别脑补，宁可问她。）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
