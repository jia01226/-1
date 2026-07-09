"""聊天：SSE 对话、历史消息、会话抽屉、模型选择器，以及 /chat 页面。"""
import json
import logging
from flask import Blueprint, Response, jsonify, request, send_from_directory

import db
import chat_ai
from constants import (STATIC_DIR, MAIN_SESSION, SESSION_NAME_MAXLEN,
                       DEFAULT_SESSION_NAME, USAGE_TAG, THINK_TAG,
                       SSE_CONTENT_TYPE, SSE_HEADERS)
from utils import guard, jbody, jget

logger = logging.getLogger(__name__)
bp = Blueprint("chat", __name__)


@bp.get("/chat")
def chat_page(): return send_from_directory(STATIC_DIR, "chat.html")


def _chat_sid(raw):
    """把前端传来的会话 id 收敛成合法的 1对1 会话 id：非法/群聊/不存在都退回主对话 1。"""
    try:
        sid = int(raw)
    except (TypeError, ValueError):
        return MAIN_SESSION
    if sid == db.GROUP_SID or not db.session_exists(sid):
        return MAIN_SESSION
    return sid


@bp.post("/api/chat")
@guard
def api_chat():
    data = jbody()
    text = (data.get("text") or "").strip()
    image = (data.get("image") or "").strip()
    if not text and not image:
        return jsonify({"error": "empty"}), 400
    sid = _chat_sid(data.get("session_id"))
    bedroom = bool(data.get("bedroom"))                # 卧室模式（bedroom.py 只在服务器本地）
    if bedroom:
        logger.info("[bedroom] 前端的卧室开关已送达后端")
    model = chat_ai.resolve_model(data.get("model"))   # 前端可选模型，白名单外回落默认
    db.add_message("user", text, session_id=sid, image=image, msg_type=("image" if image else "text"))
    history = db.recent_messages(session_id=sid)
    posts = db.app_posts()   # app 里的助手看 both+app（含只在 app 的悄悄话）

    def gen():
        acc = ""
        for piece in chat_ai.stream_chat(history, posts, model=model, bedroom=bedroom):
            if isinstance(piece, tuple):
                if piece[0] == USAGE_TAG:
                    usage = piece[1] or {}
                    cost, it, ot = chat_ai.estimate_cost(model, usage)
                    db.log_usage(model, it, ot, cost)
                elif piece[0] == THINK_TAG:
                    yield ("data: " + json.dumps({"think": piece[1]}, ensure_ascii=False) + "\n\n").encode("utf-8")
                continue
            acc += piece
            yield ("data: " + json.dumps({"t": piece}, ensure_ascii=False) + "\n\n").encode("utf-8")
        if acc:
            db.add_message("assistant", acc, session_id=sid)
        yield ("data: " + json.dumps({"done": True}, ensure_ascii=False) + "\n\n").encode("utf-8")

    return Response(gen(), content_type=SSE_CONTENT_TYPE, headers=dict(SSE_HEADERS))


@bp.get("/api/models")
@guard
def api_models():
    """给前端模型选择器（知言的 UI 调这个）：可选模型（白名单）+ 当前默认。"""
    return jsonify({"models": chat_ai.MODEL_WHITELIST, "default": chat_ai.MODEL})


@bp.get("/api/messages")
@guard
def api_messages():
    sid = _chat_sid(request.args.get("session_id"))
    return jsonify(db.recent_messages(session_id=sid, limit=200))


@bp.post("/api/messages/delete")
@guard
def api_delete_message():
    mid = jget("id")
    if not mid:
        return jsonify({"error": "need id"}), 400
    db.delete_message(mid)
    return jsonify({"ok": True})


# ---- 会话抽屉（多条 1对1 对话）----
@bp.get("/api/sessions")
@guard
def api_sessions(): return jsonify(db.list_chat_sessions())


@bp.post("/api/sessions")
@guard
def api_session_new():
    name = (jget("name") or DEFAULT_SESSION_NAME).strip()[:SESSION_NAME_MAXLEN] or DEFAULT_SESSION_NAME
    return jsonify({"id": db.create_chat_session(name), "name": name})


@bp.post("/api/sessions/rename")
@guard
def api_session_rename():
    d = jbody()
    name = (d.get("name") or "").strip()[:SESSION_NAME_MAXLEN]
    if not d.get("id") or not name:
        return jsonify({"error": "need id+name"}), 400
    db.rename_chat_session(d["id"], name)
    return jsonify({"ok": True})


@bp.post("/api/sessions/delete")
@guard
def api_session_delete():
    ok = db.delete_chat_session(jget("id"))
    return jsonify({"ok": ok})
