# 日麻对局预约系统

## 项目简介

这是一个基于 Django 框架构建的日式麻将（日麻）对局预约与管理系统。它旨在为麻将馆门店提供一套完整的在线预约解决方案，同时为玩家提供方便的对局信息查看、约桌、凑桌及取消功能。管理员可以通过强大的后台界面进行门店、牌桌及对局记录的全面管理和数据导出。

## 主要功能

*   **门店对局情况查看**：
    *   用户无需登录即可查看各门店的实时对局情况及牌桌空闲状态。
    *   对局中的牌桌会显示当前对局者信息、预约类型（按半庄数或时间段）及起止时间。
    *   提供图形化（日程表式）时间视图，直观展示未来24小时内各桌的预约占用情况。
*   **用户预约与凑桌**：
    *   用户登录后可发起新的对局预约，选择按**半庄数**或**固定时间段**进行预约。
    *   支持用户加入其他玩家发起的“等待凑齐”的对局。
    *   当对局人数达到4人时，系统将自动匹配成功，并从等待列表中移除。
    *   用户可在“我的对局”页面查看自己已发起或已加入预约的详细信息。
    *   支持取消“等待凑齐”的预约（退出不影响他人）；支持取消“已成行”的对局（需在对局开始前1小时以上），取消后该对局会退回“等待凑齐”状态。
*   **管理员操作与管理**：
    *   提供功能强大的 Django Admin 后台管理界面。
    *   管理员可对门店、麻将桌、用户及所有对局记录进行增删改查。
    *   支持为已成行的对局手动分配空闲牌桌，并进行时间冲突检测。
    *   支持为特定牌桌快速创建“散客对局”（模拟现场占用）。
    *   **支持将选定的对局记录导出为 XLSX 格式文件**，包含所有详细信息（发起人、参与者、门店、牌桌、时间、状态等）。
    *   **新增“课表导出”功能**：在后台列表选中需要的记录并指定日期范围，系统会按天 / 门店生成类似预约时间表的 Excel，每小时分格展示每张牌桌的占用情况，便于打印和对外张贴。
    *   用户管理支持中文用户名（通过 `CustomUser` 模型实现）。

## 技术栈

*   **后端**: Python 3.12+ (Django 框架)
*   **数据库**: SQLite (开发环境), PostgreSQL (生产环境推荐)
*   **异步任务/定时任务**: Celery + Redis
*   **Excel 导出**: openpyxl
*   **前端**: HTML, CSS (Django 模板引擎)

## 快速启动指南

以下步骤将指导您在本地环境中快速设置和运行项目。

### 1. 克隆仓库

首先，将项目仓库克隆到您的本地机器：

```bash
git clone https://github.com/Persistentsteed/mahjong-booking-system.git
cd mahjong-booking-system
```

### 2. 环境设置 (自动化脚本)

我们提供了一个自动化脚本来帮助您安装依赖、初始化数据库和创建超级用户。

#### macOS / Linux 用户

1. **赋予脚本执行权限**:

   ```bash
   chmod +x setup.sh
   ```

2. **运行设置脚本**:

   ```bash
   ./setup.sh
   ```

   脚本将引导您：

   *   创建并激活 Python 虚拟环境。
   *   安装所有必要的 Python 依赖。
   *   清理旧的数据库和迁移文件。
   *   应用所有数据库迁移。
   *   提示您创建一个 Django 超级用户（管理员账号）。
   *   自动导入默认的门店和麻将桌数据。

#### Windows 用户

1. **打开命令提示符 (CMD) 或 PowerShell**，导航到项目根目录。

2. **运行设置脚本**:

   ```bash
   setup.bat
   ```

   脚本将执行类似 macOS/Linux 的步骤。请注意，在 Windows 上，您可能需要在删除 `migrations` 文件时手动确认，并且 `createsuperuser` 可能会直接提示您输入用户名和密码。

### 3. 安装并启动 Redis

Celery 任务队列和定时任务需要 Redis 服务来运行。请确保您的系统上已安装并运行 Redis。

* **macOS (使用 Homebrew)**:

  ```bash
  brew install redis
  brew services start redis
  ```

* **Linux (Debian/Ubuntu)**:

  ```bash
  sudo apt-get update
  sudo apt-get install redis-server
  sudo systemctl start redis
  sudo systemctl enable redis
  ```

* **Windows**:
  推荐前往 [Redis 官网](https://redis.io/download/) 下载 MSOpenTech 提供的稳定版本或使用 Scoop/Chocolatey 包管理器安装。启动 Redis 服务器后，它通常会监听 `localhost:6379`。

### 4. 启动项目服务

项目包含三个独立的服务进程，需要在三个不同的终端窗口中分别启动。

#### 终端 1: 启动 Django Web 服务器

导航到项目根目录，激活虚拟环境，并启动 Django 开发服务器：

* **macOS / Linux**:

  ```bash
  source venv/bin/activate
  python manage.py runserver
  ```

* **Windows**:

  ```bash
  .\venv\Scripts\activate.bat
  python manage.py runserver
  ```

  这将启动 Web 应用，您可以在浏览器中访问 `http://127.0.0.1:8000/`。

#### 终端 2: 启动 Celery Worker (任务执行者)

在**第二个新的终端窗口**中，导航到项目根目录，激活虚拟环境，并启动 Celery Worker：

* **macOS / Linux**:

  ```bash
  source venv/bin/activate
  celery -A config worker -l info
  ```

* **Windows**:

  ```bash
  .\venv\Scripts\activate.bat
  celery -A config worker -l info
  ```

#### 终端 3: 启动 Celery Beat (定时调度器)

在**第三个新的终端窗口**中，导航到项目根目录，激活虚拟环境，并启动 Celery Beat：

* **macOS / Linux**:

  ```bash
  source venv/bin/activate
  celery -A config beat -l info
  ```

* **Windows**:

  ```bash
  .\venv\Scripts\activate.bat
  celery -A config beat -l info
  ```

### 5. 访问应用

所有服务启动后，在浏览器中访问：

*   **项目主页**: `http://127.0.0.1:8000/`
*   **Django Admin 后台**: `http://127.0.0.1:8000/admin/` (使用您创建的超级用户登录)

## 数据库与静态文件 (生产环境考虑)

在生产环境中，您需要将 `db.sqlite3` 替换为更强大的数据库（如 PostgreSQL），并部署静态文件：

*   **数据库**: 修改 `config/settings.py` 中的 `DATABASES` 配置。
*   **静态文件**: 运行 `python manage.py collectstatic` 并配置您的 Web 服务器（如 Nginx, Gunicorn）来提供静态文件。

## 如何贡献

欢迎对该项目提出改进意见或贡献代码！

1.  Fork 本仓库。
2.  创建您的功能分支 (`git checkout -b feature/AmazingFeature`)。
3.  提交您的修改 (`git commit -m 'Add some AmazingFeature'`)。
4.  将分支推送到远程 (`git push origin feature/AmazingFeature`)。
5.  创建一个 Pull Request。

## 许可证

该项目根据 MIT 许可证发布。

## 联系方式

如果您有任何问题或建议，欢迎联系我：Github:Persistentsteed
