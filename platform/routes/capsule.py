"""时间胶囊：没到开启日只给标题和倒计时。"""
import datetime
import logging
from flask import Blueprint, jsonify, send_from_directory

import db
from constants import STATIC_DIR
from utils import guard, jbody, jget

logger = logging.getLogger(__name__)
bp = Blueprint("capsule", __name__)


@bp.get("/capsule")
def capsule_page(): return send_from_directory(STATIC_DIR, "capsule.html")


@bp.get("/api/capsules")
@guard
def api_capsules():
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date().isoformat()
    out = []
    for c in db.all_capsules():
        opened = c["open_at"] <= today
        out.append({**c, "opened": opened,
                    # 没到开启日：藏正文和图，只留标题和倒计时
                    "content": c["content"] if opened else "",
                    "image": c["image"] if opened else "",
                    "days_left": (datetime.date.fromisoformat(c["open_at"]) - datetime.date.fromisoformat(today)).days})
    return jsonify(out)


@bp.post("/api/capsules")
@guard
def api_capsule_add():
    d = jbody()
    title = (d.get("title") or "").strip()
    content = (d.get("content") or "").strip()
    open_at = (d.get("open_at") or "").strip()
    if not title or not content or not open_at:
        return jsonify({"error": "need title+content+open_at"}), 400
    return jsonify({"id": db.add_capsule(title, content, open_at, (d.get("image") or "").strip())})


@bp.post("/api/capsules/delete")
@guard
def api_capsule_del():
    db.delete_capsule(jget("id"))
    return jsonify({"ok": True})
