#!/usr/bin/env python3
"""批量把「记忆卡片」导入 posts 记忆库（配合 memory 切割的 L2 卡片层）。

用法：
    python import_memories.py cards.txt              # 正式导入
    python import_memories.py cards.txt --dry-run    # 只预览解析结果，不写库
    python import_memories.py cards.txt --no-vector  # 导入但不建向量（本地没配 embedding 时）

卡片文件格式（一行一条，对齐 kongkong《记忆切割规格》）：
    [EVENT|both] 2026-07 新疆那拉提：佳佳抱小白羊羔……
    [MEMORY] 称呼红线：别叫"沛沛"……            # visibility 省略＝both
  - 空行、以 # 或 > 开头的注释行、``` 围栏标记行，一律忽略（围栏里的卡片照常解析）。
  - type 只认：MEMORY/EVENT/MOMENT/PROMISE/WISHLIST；visibility 只认：both/app/repo。

🔒 隐私铁律（别忘）：只把「非私密」卡片放进这个文件。
   单聊和群聊都读 posts——私密内容一旦进库，会漏给群聊里的小克/知言。
   私密记忆（xp 细节、家里的事、崩溃那晚、健康）留常驻魂文件，别切进这里。
"""
import sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

TYPES = {"MEMORY", "EVENT", "MOMENT", "PROMISE", "WISHLIST"}
VIS = {"both", "app", "repo"}
LINE = re.compile(r"^\[\s*([A-Za-z]+)\s*(?:\|\s*([A-Za-z]+)\s*)?\]\s*(.+?)\s*$")


def parse(path):
    """解析卡片文件 → ([(type, visibility, content), ...], [告警, ...])。"""
    cards, warns = [], []
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            s = raw.strip()
            if not s or s.startswith("```") or s.startswith("#") or s.startswith(">"):
                continue
            m = LINE.match(s)
            if not m:
                warns.append(f"第{n}行不认识、跳过：{s[:40]}")
                continue
            t = m.group(1).upper()
            v = (m.group(2) or "both").lower()
            c = m.group(3).strip()
            if t not in TYPES:
                warns.append(f"第{n}行 type『{t}』非法、跳过：{s[:40]}")
                continue
            if v not in VIS:
                warns.append(f"第{n}行 visibility『{v}』非法、当 both：{s[:40]}")
                v = "both"
            if c:
                cards.append((t, v, c))
            else:
                warns.append(f"第{n}行内容为空、跳过")
    return cards, warns


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    no_vec = "--no-vector" in args
    files = [a for a in args if not a.startswith("--")]
    if not files:
        print(__doc__)
        sys.exit(1)
    path = files[0]
    if not os.path.exists(path):
        print(f"找不到文件：{path}")
        sys.exit(1)

    db.init_db()   # 独立跑时确保表在（服务器上无害，幂等）
    cards, warns = parse(path)
    for w in warns:
        print("⚠️ ", w)
    tag = "（--dry-run 预览，不写库）" if dry else ""
    print(f"\n解析到 {len(cards)} 条卡片{tag}：")
    for t, v, c in cards:
        print(f"  [{t}|{v}] {c[:60]}{'…' if len(c) > 60 else ''}")
    if dry or not cards:
        return

    # 防重：库里已有的完全相同 content 跳过（脚本可安全地重复跑）
    existing = {p["content"] for p in db.all_posts()}
    added = skipped = vec_ok = 0
    vector_search = None
    if not no_vec:
        try:
            import vector_search as vs
            vector_search = vs
        except Exception as e:
            print("向量模块加载失败，仅导入不建向量：", e)

    for t, v, c in cards:
        if c in existing:
            skipped += 1
            continue
        pid = db.add_post(t, c, v)
        existing.add(c)
        added += 1
        if vector_search:
            try:
                if vector_search.index_post(pid, c):
                    vec_ok += 1
            except Exception as e:
                print("  向量跳过：", e)

    print(f"\n✅ 导入完成：新增 {added} 条，跳过重复 {skipped} 条，建向量 {vec_ok} 条。")
    if vector_search and vec_ok < added:
        print("   （建向量数 < 新增数：多半是没配 embedding；在服务器配好后重跑即可补建。）")


if __name__ == "__main__":
    main()
