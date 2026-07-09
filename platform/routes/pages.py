"""杂项：首页/静态文件/sw.js、登录、用量汇总。
（各功能自己的页面路由跟功能蓝图放在一起，如 /diary 在 diary.py。）
"""
import logging
from flask import Blueprint, jsonify, session, send_from_directory

import db
from constants import STATIC_DIR, PASSCODE
from utils import guard, jget

logger = logging.getLogger(__name__)
bp = Blueprint("pages", __name__)


@bp.post("/api/login")
def login():
    session.permanent = True   # 让登录长期记住，不再每次都问
    if not PASSCODE:
        session["ok"] = True; return jsonify({"ok": True})
    if jget("passcode") == PASSCODE:
        session["ok"] = True; return jsonify({"ok": True})
    return jsonify({"ok": False}), 401


@bp.get("/")
def home(): return send_from_directory(STATIC_DIR, "index.html")


@bp.get("/static/<path:p>")
def static_files(p): return send_from_directory(STATIC_DIR, p)


@bp.get("/sw.js")
def sw_js():
    # service worker 必须从根目录提供，作用域才能覆盖整个站点
    return send_from_directory(STATIC_DIR, "sw.js", mimetype="application/javascript")


@bp.get("/api/usage")
@guard
def api_usage(): return jsonify(db.usage_summary())
