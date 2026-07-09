"""共读：书目、原文、批注（自己写或请角色写）。"""
import os
import logging
from flask import Blueprint, jsonify, request, send_from_directory

import db
import chat_ai
from constants import STATIC_DIR
from utils import guard, jbody, jget

logger = logging.getLogger(__name__)
bp = Blueprint("reading", __name__)


@bp.get("/reading")
def reading_page(): return send_from_directory(STATIC_DIR, "reading.html")


@bp.get("/api/readings")
@guard
def api_readings(): return jsonify(db.all_readings())


@bp.post("/api/readings")
@guard
def api_reading_add():
    d = jbody()
    title = (d.get("title") or "").strip()
    content = (d.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "need title+content"}), 400
    return jsonify({"id": db.add_reading(title, (d.get("author") or "").strip(), content)})


@bp.get("/api/reading")
@guard
def api_reading_one():
    r = db.get_reading(request.args.get("id"))
    if not r:
        return jsonify({"error": "not found"}), 404
    r["paras"] = [p for p in r["content"].split("\n") if p.strip()]
    r["annotations"] = db.reading_annotations(r["id"])
    return jsonify(r)


@bp.post("/api/readings/delete")
@guard
def api_reading_del():
    db.delete_reading(jget("id"))
    return jsonify({"ok": True})


@bp.post("/api/reading/annotate")
@guard
def api_reading_annotate():
    """我写批注(author=user)，或请角色写(ai=1)。"""
    d = jbody()
    rid = d.get("id"); para = d.get("para")
    if rid is None or para is None:
        return jsonify({"error": "need id+para"}), 400
    if d.get("ai"):
        r = db.get_reading(rid)
        paras = [p for p in (r["content"].split("\n") if r else []) if p.strip()]
        if not r or para >= len(paras):
            return jsonify({"error": "bad para"}), 400
        who = os.environ.get("CHARACTER", "").strip() or "TA"
        text = chat_ai.annotate_passage(r["title"], r["author"], paras[para])
        if not text:
            return jsonify({"error": "生成失败，再试一次"}), 200
        aid = db.add_annotation(rid, para, who, text)
        return jsonify({"id": aid, "author": who, "content": text})
    content = (d.get("content") or "").strip()
    if not content:
        return jsonify({"error": "empty"}), 400
    aid = db.add_annotation(rid, para, "user", content)
    return jsonify({"id": aid, "author": "user", "content": content})
