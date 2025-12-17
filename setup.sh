#!/usr/bin/env bash
# 自动化初始化脚本 (macOS / Linux)
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== Mahjong Booking System 环境初始化 (macOS/Linux) ==="

# 1. 检查 Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "未检测到 python3，请先安装 Python 3.10+。"
    exit 1
fi

# 2. 创建 / 激活虚拟环境
VENV_DIR="${PROJECT_ROOT}/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/6] 创建虚拟环境：$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi
echo "激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 3. 安装依赖
echo "[2/6] 升级 pip / wheel / setuptools"
python -m pip install --upgrade pip setuptools wheel
echo "[3/6] 安装项目依赖 (requirements.txt)"
pip install -r requirements.txt

# 4. 运行数据库迁移
echo "[4/6] 同步数据库结构"
python manage.py migrate --noinput

# 5. 创建超级用户（若不存在）
echo "[5/6] 检查超级用户..."
if python manage.py shell -c "from django.contrib.auth import get_user_model;import sys;User=get_user_model();sys.exit(0 if User.objects.filter(is_superuser=True).exists() else 1)"; then
    echo "已存在超级用户，跳过创建。"
else
    echo "创建第一个超级用户，请按提示输入账号信息。"
    python manage.py createsuperuser
fi

# 6. 导入默认门店与牌桌（仅首次）
echo "[6/6] 导入默认门店/牌桌（如果尚不存在）"
python manage.py shell < scripts/seed_default_data.py

deactivate

cat <<'INSTRUCTIONS'

=== 下一步操作 ===
1. 确保 Redis 已安装并运行 (macOS: brew services start redis / Linux: systemctl start redis)。
2. 分别在三个终端激活虚拟环境并启动：
   a. Web 服务器:   source venv/bin/activate && python manage.py runserver
   b. Celery Worker: source venv/bin/activate && celery -A config worker -l info
   c. Celery Beat:   source venv/bin/activate && celery -A config beat -l info

提示：如需重新执行脚本，可删除 venv 或 db 文件后再次运行。
=== 初始化完成 ===
INSTRUCTIONS
