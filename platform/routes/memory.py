"""记忆库（posts）与向量索引。"""
import logging
from flask import Blueprint, jsonify

import db
from utils import guard, jbody, jget

logger = logging.getLogger(__name__)
bp = Blueprint("memory", __name__)


@bp.get("/api/posts")
@guard
def api_posts(): return jsonify(db.all_posts())


@bp.post("/api/posts")
@guard
def api_add_post():
    d = jbody()
    content = d.get("content", "").strip()
    pid = db.add_post(d.get("type", "MEMORY"), content, d.get("visibility", "both"))
    # 新记忆顺手建一条向量（失败不影响保存）
    try:
        import vector_search
        vector_search.index_post(pid, content)
    except Exception as e:
        logger.warning("索引新记忆失败：%s", e)
    return jsonify({"id": pid})


@bp.post("/api/posts/delete")
@guard
def api_delete_post():
    pid = jget("id")
    if not pid:
        return jsonify({"error": "need id"}), 400
    db.delete_post(pid)
    return jsonify({"ok": True})


@bp.get("/api/vector/status")
@guard
def api_vector_status():
    import vector_search
    return jsonify({
        "backend": vector_search.EMBED_BACKEND,
        "model": vector_search.EMBED_MODEL,
        "available": vector_search.available(),
        "indexed": db.embedding_count(vector_search.EMBED_MODEL),
        "posts": len(db.all_posts()),
    })


@bp.post("/api/vector/backfill")
@guard
def api_vector_backfill():
    import vector_search
    n = vector_search.backfill()
    return jsonify({"indexed_new": n})
