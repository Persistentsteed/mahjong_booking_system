#!/bin/bash
# 这个脚本用于在 macOS 和 Linux 环境下自动化设置 Django 项目

echo "--- 开始设置 Mahjong Booking System (macOS/Linux) ---"

# 1. 检查 Python 3 环境
if ! command -v python3 &> /dev/null
then
    echo "错误：未找到 python3。请先安装 Python 3.x。"
    exit 1
fi

# 2. 创建并激活虚拟环境
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

echo "激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 3. 安装 Python 依赖
echo "安装 Python 依赖（来自 requirements.txt）..."
pip install -r requirements.txt

# 4. 检查 Redis 服务 (提示用户手动检查)
echo "------------------------------------------------------------------"
echo "重要：请手动确保 Redis 服务正在运行。"
echo "  - macOS 用户通常通过 'brew install redis' 安装，'brew services start redis' 启动。"
echo "  - Linux 用户通常通过 'sudo apt-get install redis-server' 安装，'sudo systemctl start redis' 启动。"
echo "  （如果 Redis 未运行，Celery Worker & Beat 将无法启动）"
echo "------------------------------------------------------------------"
sleep 3 # 暂停3秒，让用户阅读提示

# 5. 清理旧数据和数据库迁移文件 (确保全新初始化)
echo "清理旧的数据库文件和 migrations 目录..."
if [ -f "db.sqlite3" ]; then
    rm "db.sqlite3"
fi
# 删除所有 app/migrations/ 下的 .py 文件 (除了 __init__.py)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -name "__pycache__" -exec rm -rf {} + # 清理所有 Python 缓存

# 6. 应用数据库迁移
echo "应用数据库迁移..."
python manage.py makemigrations accounts booking # 为指定 app 生成，避免不必要的操作
python manage.py migrate

# 7. 创建超级用户
echo "--- 创建 Django 超级用户 ---"
echo "请为您的管理员账号设置用户名和密码。"
python manage.py createsuperuser --noinput # 使用 --noinput，脚本会尝试创建，如果已存在就不会提示

# 8. 导入初始业务数据 (门店和麻将桌)
echo "导入初始业务数据（门店和麻将桌）..."
python manage.py shell -c """
from booking.models import Store, MahjongTable
if not Store.objects.exists():
    print('正在创建默认门店和麻将桌数据...')
    store1, _ = Store.objects.get_or_create(name='大钟寺', defaults={'address': '北京市海淀区大钟寺'})
    for i in range(1, 5): 
        MahjongTable.objects.get_or_create(store=store1, table_number=f'大钟寺 - {i}')
    
    store2, _ = Store.objects.get_or_create(name='五道口', defaults={'address': '北京市海淀区五道口购物中心'})
    for i in range(1, 8):
        MahjongTable.objects.get_or_create(store=store2, table_number=f'五道口 - {i}')

    store3, _ = Store.objects.get_or_create(name='三里屯', defaults={'address': '北京市朝阳区三里屯'})
    for i in range(1, 6):
        MahjongTable.objects.get_or_create(store=store3, table_number=f'三里屯 - {i}')

    store4, _ = Store.objects.get_or_create(name='国贸', defaults={'address': '北京市朝阳区国贸CBD'})
    for i in range(1, 9):
        MahjongTable.objects.get_or_create(store=store4, table_number=f'国贸 - {i}')
    
    print('默认门店和麻将桌数据创建完成。')
else:
    print('门店数据已存在，跳过导入。')
"""

echo "--- 设置完成！项目已准备就绪 ---"
echo "要启动项目，请在三个独立的终端中，分别执行以下命令（请确保在各自终端中也激活了虚拟环境）："
echo ""
echo "1. 启动 Django Web 服务器："
echo "   source venv/bin/activate && python manage.py runserver"
echo ""
echo "2. 启动 Celery Worker："
echo "   source venv/bin/activate && celery -A config worker -l info"
echo ""
echo "3. 启动 Celery Beat (定时调度器)："
echo "   source venv/bin/activate && celery -A config beat -l info"
echo ""
echo "请记住：在运行 Celery 进程之前，Redis 必须运行！"