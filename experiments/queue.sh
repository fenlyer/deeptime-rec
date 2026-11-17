#!/usr/bin/env bash
# queue.sh — 后台实验队列（W0-c）
#
# 逐行读取 experiments/queue.txt，在 tmux 会话 exp 中顺序执行。
# 每行执行后向 experiments/queue.log 追加：开始时间、结束时间、退出码、命令。
# 执行过的行在 queue.txt 中加上前缀 "# done "，避免重复运行。
#
# 用法：
#   bash experiments/queue.sh              # 后台运行（自动建 tmux 会话 exp）
#   bash experiments/queue.sh --foreground # 前台运行，便于调试
#   bash experiments/queue.sh --dry-run    # 只列出待执行命令，不执行
#   bash experiments/queue.sh --status     # 查看队列进度
#
# 约定：
#   - queue.txt 中空行和以 # 开头的行被忽略
#   - 命令在本脚本所在仓库根目录下执行
#   - 任一条失败不中断队列，继续执行下一条（退出码记录在日志里）

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUEUE_FILE="$REPO_ROOT/experiments/queue.txt"
LOG_FILE="$REPO_ROOT/experiments/queue.log"
TMUX_SESSION="exp"
MODE="tmux"

for arg in "$@"; do
  case "$arg" in
    --foreground) MODE="foreground" ;;
    --dry-run)    MODE="dry-run" ;;
    --status)     MODE="status" ;;
    -h|--help)    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf '未知参数：%s\n' "$arg" >&2; exit 1 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf '错误：%s\n' "$*" >&2; exit 1; }

# ------------------------------------------------------------ 主循环（worker）
run_queue() {
  cd "$REPO_ROOT" || die "无法进入仓库根目录"

  local idx=0 total=0
  total=$(grep -cvE '^\s*(#|$)' "$QUEUE_FILE" 2>/dev/null || echo 0)
  say "队列启动：共 $total 条待执行命令"
  say "日志：$LOG_FILE"
  say "开始时间：$(date -Iseconds)"
  say ""

  # 逐行读取，边读边执行。不在循环内改 queue.txt，避免读到改动的文件；
  # 需要标记的行先收集到 DONE_LINES，循环结束后统一回写。
  # bash 3.2（macOS 自带）没有 mapfile，这里用 while read 写法。
  local DONE_LINES=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    # 跳过空行与注释（含已标记 # done 的行）
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    idx=$((idx + 1))
    local start_ts end_ts rc t0 elapsed

    start_ts=$(date -Iseconds)
    say "[$idx/$total] $line"
    say "    开始 $start_ts"

    # 执行命令，记录本条耗时（用 SECONDS 差分，避免 nproc 等命令不可用）
    t0=$SECONDS
    bash -c "$line" </dev/null
    rc=$?
    elapsed=$((SECONDS - t0))

    end_ts=$(date -Iseconds)

    {
      printf '=== [%d] %s\n' "$idx" "$line"
      printf 'start=%s\n' "$start_ts"
      printf 'end=%s\n' "$end_ts"
      printf 'exit_code=%d\n' "$rc"
      printf 'elapsed_s=%s\n\n' "$elapsed"
    } >> "$LOG_FILE"

    if [[ $rc -eq 0 ]]; then
      say "    完成 $end_ts  exit=0"
    else
      say "    失败 $end_ts  exit=$rc"
    fi

    # 用换行累积待标记行，循环结束后一次性回写
    if [[ -z "$DONE_LINES" ]]; then
      DONE_LINES="$line"
    else
      DONE_LINES="$DONE_LINES
$line"
    fi
  done < "$QUEUE_FILE"

  # 统一给执行过的行加 # done 前缀（按首次匹配标记，同名命令只标记一次）
  if [[ -n "$DONE_LINES" ]]; then
    local tmp
    tmp="$(mktemp)"
    printf '%s\n' "$DONE_LINES" > "$tmp.done"
    awk 'NR == FNR { done[$0] = 1; next }
         ($0 in done) && !done_marked[$0] { print "# done " $0; done_marked[$0] = 1; next }
         { print }' "$tmp.done" "$QUEUE_FILE" > "$tmp"
    mv "$tmp" "$QUEUE_FILE"
    rm -f "$tmp.done"
  fi

  say ""
  say "队列结束。共执行 $idx 条。"
  say "统计：成功 $(grep -c 'exit_code=0' "$LOG_FILE" 2>/dev/null || echo 0) 条"
}

# ------------------------------------------------------------------- 模式分发
[[ -f "$QUEUE_FILE" ]] || { touch "$QUEUE_FILE"; say "已创建空的 $QUEUE_FILE"; }

case "$MODE" in
  dry-run)
    say "待执行命令（dry-run，不会执行）："
    grep -nvE '^\s*(#|$)' "$QUEUE_FILE" | sed 's/^/  /' || say "  （空）"
    ;;

  status)
    pending=$(grep -cvE '^\s*(#|$)' "$QUEUE_FILE" 2>/dev/null); pending=${pending:-0}
    done_count=$(grep -c '^# done ' "$QUEUE_FILE" 2>/dev/null); done_count=${done_count:-0}
    say "队列状态"
    say "  文件：$QUEUE_FILE"
    say "  待执行：$pending 条"
    say "  已完成：$done_count 条"
    if [[ -f "$LOG_FILE" ]]; then
      log_lines=$(wc -l < "$LOG_FILE" | tr -d ' ')
      say "  日志：${LOG_FILE} （${log_lines} 行）"
      say ""
      say "  最近 5 次执行："
      grep -E '^(===|exit_code=)' "$LOG_FILE" | tail -10 | sed 's/^/    /'
    else
      say "  日志：尚未生成"
    fi
    ;;

  foreground)
    run_queue
    ;;

  tmux)
    command -v tmux >/dev/null 2>&1 || \
      die "未找到 tmux。请先安装 tmux，或改用 --foreground 模式（会占用当前终端）"

    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
      say "tmux 会话 $TMUX_SESSION 已存在，请先查看或结束它："
      say "  tmux attach -t $TMUX_SESSION    # 进入查看"
      say "  tmux kill-session -t $TMUX_SESSION  # 结束后重开"
      exit 1
    fi

    # 把 worker 逻辑写成临时脚本再交给 tmux，避免引号嵌套问题
    WORKER=$(mktemp "${TMPDIR:-/tmp}/queue_worker.XXXXXX.sh")
    {
      printf '#!/usr/bin/env bash\n'
      printf 'set -uo pipefail\n'
      # 变量必须先定义，函数体在运行时才解析变量
      printf 'REPO_ROOT=%q\n' "$REPO_ROOT"
      printf 'QUEUE_FILE=%q\n' "$QUEUE_FILE"
      printf 'LOG_FILE=%q\n' "$LOG_FILE"
      declare -f say die run_queue
      printf 'run_queue\n'
    } > "$WORKER"
    chmod +x "$WORKER"

    tmux new-session -d -s "$TMUX_SESSION" "bash '$WORKER'; rm -f '$WORKER'"

    say "队列已在 tmux 会话 $TMUX_SESSION 中启动。"
    say "  查看进度：tmux attach -t $TMUX_SESSION"
    say "  查看日志：tail -f $LOG_FILE"
    say "  队列状态：bash experiments/queue.sh --status"
    ;;

  *)
    die "未知模式：$MODE"
    ;;
esac
