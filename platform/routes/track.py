"""手机行踪 / 健康数据上报（iOS 快捷指令，token 校验）与活动查询。"""
import os
import logging
from flask import Blueprint, jsonify, request, session

import db
from constants import PASSCODE
from utils import guard

logger = logging.getLogger(__name__)
bp = Blueprint("track", __name__)


# 快捷指令不方便带登录态，所以用 token 校验（.env 里 TRACK_TOKEN，缺省用访问口令）。
@bp.route("/api/track", methods=["POST", "GET"])
def api_track():
    d = request.get_json(silent=True) or request.form or {}
    app_name = (d.get("app") or request.args.get("app") or "").strip()
    detail = (d.get("detail") or request.args.get("detail") or "").strip()
    token = (d.get("token") or request.args.get("token") or "").strip()
    need = os.environ.get("TRACK_TOKEN", "").strip() or PASSCODE
    if need and token != need:
        return jsonify({"error": "bad token"}), 403
    if not app_name:
        return jsonify({"error": "need app"}), 400
    db.add_activity(app_name, detail)
    return jsonify({"ok": True})


@bp.get("/api/activity")
@guard
def api_activity(): return jsonify(db.recent_activity(limit=50))


# ---- 健康数据（Apple Watch/快捷指令上报；主权在用户：装哪条指令才有哪类数据）----
@bp.route("/api/health", methods=["POST", "GET"])
def api_health_report():
    d = request.get_json(silent=True) or request.form or {}
    metric = (d.get("metric") or request.args.get("metric") or "").strip()
    value = d.get("value") or request.args.get("value")
    token = (d.get("token") or request.args.get("token") or "").strip()
    need = os.environ.get("TRACK_TOKEN", "").strip() or PASSCODE
    if need and token != need:
        return jsonify({"error": "bad token"}), 403
    if not metric or value is None:
        # GET 且没带参数时当查看用（需登录态）
        if request.method == "GET" and not metric:
            if PASSCODE and not session.get("ok"):
                return jsonify({"error": "need_passcode"}), 401
            return jsonify(db.recent_health(limit=50))
        return jsonify({"error": "need metric+value"}), 400
    try:
        value = float(value)
    except Exception:
        return jsonify({"error": "value must be number"}), 400
    hid = db.add_health(metric, value,
                        (d.get("unit") or request.args.get("unit") or "").strip(),
                        (d.get("detail") or request.args.get("detail") or "").strip())
    return jsonify({"ok": True, "id": hid})
