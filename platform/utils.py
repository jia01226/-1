"""路由层共用小工具：口令 guard、请求体取值 helper。"""
import functools
from flask import request, jsonify, session

from constants import PASSCODE


def guard(fn):
    """可选访问口令：设置了 ACCESS_PASSCODE 且未登录时一律 401。"""
    @functools.wraps(fn)
    def w(*a, **k):
        if PASSCODE and not session.get("ok"):
            return jsonify({"error": "need_passcode"}), 401
        return fn(*a, **k)
    return w


def jbody():
    """请求体 JSON（无 / 非法时给空 dict），替代到处写 request.json or {}。"""
    return request.json or {}


def jget(key, default=None):
    """从请求体 JSON 里取一个字段，替代 (request.json or {}).get(...)。
    default 语义与 dict.get 一致（缺省 None），保证行为与原写法逐字相同。"""
    return jbody().get(key, default)
