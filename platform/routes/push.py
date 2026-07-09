"""Web Push（助手自己的推送）。"""
import os
import json
import logging
from flask import Blueprint, jsonify

import db
from utils import guard, jbody

logger = logging.getLogger(__name__)
bp = Blueprint("push", __name__)


@bp.get("/api/push/vapid")
def push_vapid():
    import webpush_util
    return jsonify({"key": webpush_util.application_server_key()})


@bp.post("/api/push/subscribe")
@guard
def push_subscribe():
    db.add_push_subscription(json.dumps(jbody()))
    return jsonify({"ok": True})


@bp.post("/api/push/test")
@guard
def push_test():
    import webpush_util
    n = webpush_util.send_to_all(os.environ.get("APP_NAME", "助手"), "推送测试：通啦~", "/")
    return jsonify({"sent": n})
