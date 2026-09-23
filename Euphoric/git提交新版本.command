#!/bin/bash
# 用法:
#   双击本文件 (首次需先在终端执行一次: chmod +x ~/Desktop/Euphoric/*.command)
#   或在终端运行: bash git提交新版本.command "版本说明"
cd "$(dirname "$0")"

if [ -n "$1" ]; then
  MSG="$1"
else
  echo -n "输入本版本的说明 (直接回车使用默认): "
  read MSG
  [ -z "$MSG" ] && MSG="更新 $(date '+%Y-%m-%d %H:%M')"
fi

git add -A
git commit -m "$MSG" || echo "(没有改动需要提交)"

if git remote get-url origin >/dev/null 2>&1; then
  echo "检测到 GitHub 远程仓库, 正在推送..."
  git push origin HEAD || echo "推送失败: 请检查网络与 GitHub 登录状态"
else
  echo ""
  echo "⚠ 尚未连接 GitHub。首次连接方法 (二选一):"
  echo "  A. 已安装 GitHub CLI:  gh auth login  然后  gh repo create Euphoric --private --source=. --push"
  echo "  B. 手动: 在 github.com 新建空仓库后执行"
  echo "     git remote add origin <你的仓库地址>"
  echo "     git push -u origin main"
fi

echo ""
echo "=== 最近版本历史 ==="
git log --oneline -10
[ -t 0 ] && read -n 1 -s -r -p "完成, 按任意键关闭..."
