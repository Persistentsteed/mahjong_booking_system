@echo off
REM 自动化初始化脚本 (Windows CMD)
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo === Mahjong Booking System 环境初始化 (Windows) ===

REM 1. 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo 未检测到 Python， 请安装 Python 3.10+ 并添加到 PATH。
    exit /b 1
)

REM 2. 创建 / 激活虚拟环境
set "VENV_DIR=%PROJECT_ROOT%venv"
if not exist "%VENV_DIR%" (
    echo [1/6] 创建虚拟环境：%VENV_DIR%
    python -m venv "%VENV_DIR%"
)
echo 激活虚拟环境...
call "%VENV_DIR%\Scripts\activate.bat"

REM 3. 安装依赖
echo [2/6] 升级 pip / wheel / setuptools
python -m pip install --upgrade pip setuptools wheel
echo [3/6] 安装项目依赖 (requirements.txt)
pip install -r requirements.txt

REM 4. 运行数据库迁移
echo [4/6] 同步数据库结构
python manage.py migrate --noinput

REM 5. 创建超级用户（若不存在）
echo [5/6] 检查超级用户...
python manage.py shell -c "from django.contrib.auth import get_user_model; import sys; User = get_user_model(); sys.exit(0 if User.objects.filter(is_superuser=True).exists() else 1)"
if errorlevel 1 (
    echo 创建第一个超级用户，请按提示输入账号信息。
    python manage.py createsuperuser
) else (
    echo 已存在超级用户，跳过创建。
)

REM 6. 导入默认门店与牌桌
echo [6/6] 导入默认门店/牌桌（如果尚不存在）
if exist "scripts\seed_default_data.py" (
    python manage.py shell < "scripts\seed_default_data.py"
) else (
    echo 未找到 scripts\seed_default_data.py，跳过导入。
)

call deactivate

echo(
echo === 下一步操作 ===
echo 1. 确保 Redis 已安装并运行 (可使用 Scoop/Chocolatey 或官方安裝包)。
echo 2. 在三個新的終端中依次運行：
echo    a. Web 服務器:   call venv\Scripts\activate.bat ^&^& python manage.py runserver
echo    b. Celery Worker: call venv\Scripts\activate.bat ^&^& celery -A config worker -l info
echo    c. Celery Beat:   call venv\Scripts\activate.bat ^&^& celery -A config beat -l info
echo(
echo 提示：再次執行本腳本將重複安裝依賴和檢查狀態，不會刪除既有數據。
echo === 初始化完成 ===
endlocal
