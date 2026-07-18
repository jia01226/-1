"""批次灌库工具：把「记忆分层-批次X定稿」md → 直接进库（active）。

跟 import_cards.py 的分工（别混）：
  - import_cards.py = **自动初切**，机器猜，一律 pending，等柯校对+佳佳抽验。
  - 本工具        = **灌定稿**，卡片已经过开庭 judge（佳佳当庭核对过），所以直接 active/approved。

认的卡片格式（批次A/B 定稿都是这个）：
    [TYPE|scope|imp=N|source] 卡片正文……
例：
    [MEMORY|private|imp=5|user_explicit] 安全暗号：拍三下 = 立刻停……
topic 取所在的 `##` 小节标题；`>` 引用行、`---`、说明文字一律不当卡。

用法：
  预览（不写库）：  ./venv/bin/python import_batch.py ../../kongkong/记忆分层-批次B定稿-0718.md
  写库：            ./venv/bin/python import_batch.py <md> --commit
  写完补向量：      ./venv/bin/python vector_search.py backfill

铁律：灌前先 `./venv/bin/python backup_memories.py --raw`。
      同内容已在库里就跳过（content_exists），重跑安全、不会灌出双份。
"""
import os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# [TYPE|scope|imp=N|source] 正文
CARD_RE = re.compile(
    r"^\s*\[([A-Za-z_]+)\|([a-z_\-]+)\|imp=(\d)\|([a-z_]+)\]\s*(.+)$", re.S)
HEADER_RE = re.compile(r"^\s*##+\s*(.+?)\s*$")


def _load_env():
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _clean_topic(h):
    """`第一批 · B｜核心安全线（L1.5A 常驻，绝不放宽）` → `核心安全线`。"""
    t = h.split("｜")[-1] if "｜" in h else h
    t = re.sub(r"[（(].*?[）)]\s*$", "", t).strip()
    return t


def parse(md_text):
    cards, topic = [], ""
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith((">", "---")):
            continue
        h = HEADER_RE.match(line)
        if h:
            topic = _clean_topic(h.group(1))
            continue
        m = CARD_RE.match(line)
        if m:
            ctype, scope, imp, src, body = m.groups()
            cards.append({"ctype": ctype.upper(), "scope": scope, "importance": int(imp),
                          "source": src, "content": body.strip(), "topic": topic})
    return cards


def run(md_path, commit=False):
    _load_env()
    import db
    db.init_db()
    if not os.path.exists(md_path):
        print(f"✗ 找不到文件：{md_path}")
        return 1
    cards = parse(open(md_path, encoding="utf-8").read())
    if not cards:
        print("✗ 一张卡也没认出来——检查卡片格式是不是 [TYPE|scope|imp=N|source] 开头。")
        return 1

    fresh, dups = [], []
    for c in cards:
        (dups if db.content_exists(c["content"]) else fresh).append(c)

    print(f"认出定稿卡 {len(cards)} 张：新 {len(fresh)} 张，库里已有 {len(dups)} 张（跳过）。")
    for c in fresh:
        store = "私密库" if c["scope"] in ("private", "no_model") else "普通库"
        print(f"  · [{store}|imp={c['importance']}|{c['topic']}] {c['content'][:46]}…")
    if dups:
        print(f"  （跳过的 {len(dups)} 张：{'；'.join(d['content'][:20] for d in dups)}）")

    if not commit:
        print("\n（预览模式，没动库。确认无误加 --commit 写库。）")
        return 0

    n_priv = n_l2 = 0
    for c in fresh:
        if c["scope"] in ("private", "no_model"):
            db.add_private_memory(c["content"], topic=c["topic"], scope=c["scope"],
                                  source=c["source"], importance=c["importance"],
                                  review_state="approved")
            n_priv += 1
        else:
            db.ingest_card("l2", c["content"], ctype=c["ctype"], topic=c["topic"],
                           scope=c["scope"], source=c["source"],
                           importance=c["importance"], review_state="approved",
                           status="active")
            n_l2 += 1
    print(f"\n✅ 已灌库：私密库 {n_priv} 张、普通库 {n_l2} 张，全部 active（已开庭 judge 过，不走待确认）。")
    print("   下一步：./venv/bin/python vector_search.py backfill  ← 补向量，检索才找得到。")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    sys.exit(run(args[0], commit="--commit" in sys.argv))
