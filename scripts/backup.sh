#!/usr/bin/env bash
# backup.sh — 备份结果与论文源（W0-c）
#
# 同步内容：
#   results/**/metrics.json、results/**/manifest.json   每次运行的指标与清单
#   artifacts/*/manifest.json                           原型产物清单
#   thesis/、refs/、docs/                               论文源、文献、计划与决策
#
# 备份目标：默认 ~/deeptime-rec-backup，可用环境变量 BACKUP_DEST 覆盖。
# 用法：
#   make backup                    # 正常备份
#   BACKUP_DEST=/path bash scripts/backup.sh
#   bash scripts/backup.sh --dry-run   # 只看会同步什么，不写入

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DEST="${BACKUP_DEST:-$HOME/deeptime-rec-backup}"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

RSYNC_OPTS=(-a --delete-excluded)
[[ $DRY_RUN -eq 1 ]] && RSYNC_OPTS+=(--dry-run --itemize-changes)

# 排除规则：备份不需要的东西
COMMON_EXCLUDES=(
  --exclude='.DS_Store'
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='.ipynb_checkpoints/'
)

say() { printf '%s\n' "$*"; }
die() { printf '错误：%s\n' "$*" >&2; exit 1; }

[[ -d "$REPO_ROOT" ]] || die "无法定位仓库根目录"
command -v rsync >/dev/null 2>&1 || die "未找到 rsync"

say "仓库：$REPO_ROOT"
say "备份目标：$BACKUP_DEST"
[[ $DRY_RUN -eq 1 ]] && say "模式：dry-run（不写入任何文件）"
say ""

if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "$BACKUP_DEST"
fi

# ---------------------------------------------------------------- 1. results/
# 只备份 metrics.json 与 manifest.json，不备份 per_user.parquet 等大文件。
# 先 --include='*/' 让 rsync 进入所有子目录，再只放行两种文件名。
say "[1/4] results/ → metrics.json、manifest.json"
if [[ -d "$REPO_ROOT/results" ]]; then
  rsync "${RSYNC_OPTS[@]}" "${COMMON_EXCLUDES[@]}" \
    --include='*/' \
    --include='metrics.json' \
    --include='manifest.json' \
    --exclude='*' \
    "$REPO_ROOT/results/" "$BACKUP_DEST/results/"
else
  say "      results/ 不存在，跳过"
fi

# -------------------------------------------------------------- 2. artifacts/
say "[2/4] artifacts/*/manifest.json"
if [[ -d "$REPO_ROOT/artifacts" ]]; then
  rsync "${RSYNC_OPTS[@]}" "${COMMON_EXCLUDES[@]}" \
    --include='*/' \
    --include='manifest.json' \
    --exclude='*' \
    "$REPO_ROOT/artifacts/" "$BACKUP_DEST/artifacts/"
else
  say "      artifacts/ 不存在，跳过"
fi

# ------------------------------------------- 3. thesis/、refs/、docs/（整目录）
for d in thesis refs docs; do
  say "[3/4] $d/ → 整目录"
  if [[ -d "$REPO_ROOT/$d" ]]; then
    rsync "${RSYNC_OPTS[@]}" "${COMMON_EXCLUDES[@]}" \
      "$REPO_ROOT/$d/" "$BACKUP_DEST/$d/"
  else
    say "      $d/ 不存在，跳过"
  fi
done

# ---------------------------------------------------------------- 4. 备份清单
say "[4/4] 写备份清单"
if [[ $DRY_RUN -eq 0 ]]; then
  {
    printf 'backup_time=%s\n' "$(date -Iseconds)"
    printf 'hostname=%s\n' "$(hostname)"
    printf 'repo=%s\n' "$REPO_ROOT"
    printf 'git_commit=%s\n' "$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    printf 'git_dirty=%s\n' "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    printf 'data_tag=%s\n' "$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || echo none)"
  } > "$BACKUP_DEST/BACKUP_INFO.txt"
  say "      已写入 $BACKUP_DEST/BACKUP_INFO.txt"
  say ""
  say "备份完成。占用空间：$(du -sh "$BACKUP_DEST" 2>/dev/null | cut -f1)"
else
  say "      dry-run：将写入 $BACKUP_DEST/BACKUP_INFO.txt"
  say ""
  say "dry-run 完成，未写入任何文件。"
fi
