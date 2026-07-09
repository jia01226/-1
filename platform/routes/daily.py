"""日常：纪念日 / 姨妈 / 排班 / 心情 / 心事引擎。"""
import datetime
import logging
from flask import Blueprint, jsonify

import db
from utils import guard, jbody, jget

logger = logging.getLogger(__name__)
bp = Blueprint("daily", __name__)


# ---- 纪念日 ----
@bp.get("/api/anniversaries")
@guard
def api_anniv():
    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date()
    out = []
    for a in db.all_anniversaries():
        try:
            days = (today - datetime.date.fromisoformat(a["date"])).days + 1
        except Exception:
            days = None
        out.append({**a, "days": days})
    return jsonify(out)


@bp.post("/api/anniversaries")
@guard
def api_anniv_add():
    d = jbody()
    name = (d.get("name") or "").strip()
    date = (d.get("date") or "").strip()
    if not name or not date:
        return jsonify({"error": "need name+date"}), 400
    return jsonify({"id": db.add_anniversary(name, date, d.get("emoji", "💞"))})


@bp.post("/api/anniversaries/delete")
@guard
def api_anniv_del():
    db.delete_anniversary(jget("id"))
    return jsonify({"ok": True})


# ---- 姨妈 ----
@bp.get("/api/periods")
@guard
def api_periods(): return jsonify(db.recent_periods())


@bp.post("/api/periods")
@guard
def api_period_add():
    d = jbody()
    date = (d.get("start_date") or "").strip()
    if not date:
        return jsonify({"error": "need start_date"}), 400
    return jsonify({"id": db.add_period(date, d.get("note", ""))})


@bp.post("/api/periods/delete")
@guard
def api_period_del():
    db.delete_period(jget("id"))
    return jsonify({"ok": True})


# ---- 排班 ----
@bp.get("/api/shifts")
@guard
def api_shifts():
    return jsonify(db.all_shifts())


@bp.post("/api/shifts")
@guard
def api_shift_set():
    d = jbody()
    date = (d.get("date") or "").strip()
    shift = (d.get("shift") or "").strip()
    if not date or not shift:
        return jsonify({"error": "need date+shift"}), 400
    db.set_shift(date, shift, d.get("note", ""))
    return jsonify({"ok": True})


@bp.post("/api/shifts/delete")
@guard
def api_shift_del():
    db.delete_shift(jget("date"))
    return jsonify({"ok": True})


# ---- 心情记录 ----
@bp.get("/api/moods")
@guard
def api_moods(): return jsonify(db.recent_moods())


@bp.post("/api/moods")
@guard
def api_mood_add():
    d = jbody()
    mood = (d.get("mood") or "").strip()
    if not mood:
        return jsonify({"error": "need mood"}), 400
    return jsonify({"id": db.add_mood(mood, (d.get("note") or "").strip())})


# ---- 心事引擎 ----
@bp.get("/api/concerns")
@guard
def api_concerns(): return jsonify(db.all_concerns())


@bp.post("/api/concerns")
@guard
def api_concern_add():
    d = jbody()
    title = (d.get("title") or "").strip()
    if not title:
        return jsonify({"error": "need title"}), 400
    try:
        imp = max(1, min(5, int(d.get("importance", 3))))
    except Exception:
        imp = 3
    cid = db.add_concern(title, (d.get("detail") or "").strip(), imp, (d.get("next_check") or "").strip())
    return jsonify({"id": cid})


@bp.post("/api/concerns/status")
@guard
def api_concern_status():
    d = jbody()
    db.set_concern_status(d.get("id"), "resolved" if d.get("resolved") else "open")
    return jsonify({"ok": True})


@bp.post("/api/concerns/delete")
@guard
def api_concern_del():
    db.delete_concern(jget("id"))
    return jsonify({"ok": True})
