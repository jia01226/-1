#!/usr/bin/env bash
# goodlove 自动部署：定时检查 GitHub main，有新提交时先校验，再合并并重启服务。
set -Eeuo pipefail

APP_DIR="${GOODLOVE_APP_DIR:-/root/-1/platform}"
BRANCH="${GOODLOVE_BRANCH:-main}"
SERVICE_NAME="${GOODLOVE_SERVICE:-gude}"
REMOTE_REF="origin/${BRANCH}"
LOCK_FILE="/run/lock/goodlove-auto-deploy.lock"

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "已有一次自动部署正在运行，本轮跳过。"
  exit 0
fi

cd "$APP_DIR"

# 服务器上的 .env、数据库和上传文件均被 Git 忽略；这里只拦截受版本控制文件的临时改动。
if ! git diff --quiet || ! git diff --cached --quiet; then
  log "检测到服务器有未提交的代码改动，为避免覆盖，本轮停止。"
  exit 1
fi

git fetch --quiet origin "$BRANCH"

# 服务器当前提交已包含远端 main 时，无需重复部署。
if git merge-base --is-ancestor "$REMOTE_REF" HEAD; then
  exit 0
fi

CHECK_DIR="$(mktemp -d /tmp/goodlove-check.XXXXXX)"
cleanup() {
  case "$CHECK_DIR" in
    /tmp/goodlove-check.*)
      git worktree remove --force "$CHECK_DIR" >/dev/null 2>&1 || true
      rmdir "$CHECK_DIR" >/dev/null 2>&1 || true
      ;;
  esac
}
trap cleanup EXIT

git worktree add --detach --quiet "$CHECK_DIR" "$REMOTE_REF"

# 新版本先在隔离目录做 Python 语法检查；失败就保持线上旧版本继续运行。
if ! "$APP_DIR/venv/bin/python" -m compileall -q "$CHECK_DIR"; then
  log "远端代码语法检查失败，未修改线上版本。"
  exit 1
fi

# VPS 上已有的合法本地提交会被保留；若自动合并发生冲突，只撤销本次失败的合并。
if ! git merge --no-edit "$REMOTE_REF"; then
  git merge --abort >/dev/null 2>&1 || true
  log "自动合并发生冲突，已停止并保留原线上版本。"
  exit 1
fi

systemctl restart "$SERVICE_NAME"
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
  log "代码已更新，但服务启动失败，请查看 journalctl -u $SERVICE_NAME。"
  exit 1
fi

log "已同步 $REMOTE_REF，并完成 $SERVICE_NAME 重启。"
