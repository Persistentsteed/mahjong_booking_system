@echo off
REM 这个脚本用于在 Windows (CMD) 环境下自动化设置 Django 项目

echo --- 开始设置 Mahjong Booking System (Windows) ---

REM 1. 检查 Python 环境
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误：未找到 Python。请先安装 Python 3.x 并将其添加到您的系统 PATH。
    goto :eof
)

REM 2. 创建并激活虚拟环境
set VENV_DIR=venv
if not exist "%VENV_DIR%" (
    echo 创建虚拟环境...
    python -m venv "%VENV_DIR%"
)

echo 激活虚拟环境...
call "%VENV_DIR%\Scripts\activate.bat"

REM 3. 安装 Python 依赖
echo 安装 Python 依赖（来自 requirements.txt）...
pip install -r requirements.txt

REM 4. 检查 Redis 服务 (提示用户手动检查)
echo ------------------------------------------------------------------
echo 重要：请手动确保 Redis 服务正在运行。
echo   - 您需要自行安装并启动 Redis。可以从官方网站下载或使用 Scoop/Chocolatey。
echo   - 例如：'redis-server' 命令应该能启动 Redis。
echo   （如果 Redis 未运行，Celery Worker & Beat 将无法启动）"
echo ------------------------------------------------------------------"
timeout /t 3 /nobreak >nul
REM ping 127.0.0.1 -n 4 > nul (老版本cmd可能没有timeout)
echo.

REM 5. 清理旧数据和数据库迁移文件 (确保全新初始化)
echo 清理旧的数据库文件和 migrations 目录...
if exist "db.sqlite3" (
    del "db.sqlite3"
)
REM 删除所有 app/migrations/ 下的 .py 文件 (除了 __init__.py)
for /r %%i in (*.py) do (
    echo %%~nxi | findstr /i /v "__init__.py" >nul
    if %errorlevel% equ 0 (
        echo %%i | findstr /i "\migrations\" >nul
        if %errorlevel% equ 0 (
            del "%%i"
        )
    )
)
REM 清理所有 Python 缓存
for /d /r . %%d in (__pycache__) do (
    rmdir /s /q "%%d"
)

python manage.py makemigrations accounts booking
python manage.py migrate

REM 6. 创建超级用户
echo --- 创建 Django 超级用户 ---
echo 请为您的管理员账号设置用户名和密码。
REM 这里不能直接使用 --noinput，需要手动输入
python manage.py createsuperuser 

REM 7. 导入初始业务数据 (门店和麻将桌)
echo 导入初始业务数据（门店和麻将桌）...
python manage.py shell -c "from booking.models import Store, MahjongTable; from django.conf import settings; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); settings.configure(settings_module='config.settings'); if not Store.objects.exists(): print('正在创建默认门店和麻将桌数据...'); store1, _ = Store.objects.get_or_create(name='大钟寺', defaults={'address': '北京市海淀区大钟寺'}); [MahjongTable.objects.get_or_create(store=store1, table_number=f'大钟寺 - {i}') for i in range(1, 5)] ; store2, _ = Store.objects.get_or_create(name='五道口', defaults={'address': '北京市海淀区五道口购物中心'}); [MahjongTable.objects.get_or_create(store=store2, table_number=f'五道口 - {i}') for i in range(1, 8)]; print('默认门店和麻将桌数据创建完成。') else: print('门店数据已存在，跳过导入。')"

echo --- 设置完成！项目已准备就绪 ---
echo 要启动项目，请在三个独立的终端中，分别执行以下命令：
echo ""
echo "1. 启动 Django Web 服务器："
echo "   call venv\Scripts\activate.bat && python manage.py runserver"
echo ""
echo "2. 启动 Celery Worker："
echo "   call venv\Scripts\activate.bat && celery -A config worker -l info"
echo ""
echo "3. 启动 Celery Beat (定时调度器)："
echo "   call venv\Scripts\activate.bat && celery -A config beat -l info"
echo ""
echo "请记住：在运行 Celery 进程之前，Redis 必须运行！"