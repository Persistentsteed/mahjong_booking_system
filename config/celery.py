# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# 将Django的设置文件指向我们的项目
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 创建Celery实例
app = Celery('config')

# 从Django的settings.py中加载配置，所有CELERY_开头的配置项都会被读取
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有Django app下的tasks.py文件
app.autodiscover_tasks()

# --- 这里是定时任务调度器 (Celery Beat) 的配置 ---
app.conf.beat_schedule = {
    # 任务名称，可以随意取，但最好有意义
    'cleanup-expired-bookings-every-hour': {
        # 指向我们具体的任务函数
        'task': 'booking.tasks.cleanup_expired_bookings',
        # 'schedule' 定义了执行频率
        # crontab(minute='0') 表示每小时的第0分钟执行一次
        'schedule': crontab(minute='0'),
        # 这里还可以传递参数给任务，但我们的任务不需要
        # 'args': (16, 16) 
    },
    # 未来您可以在这里添加更多的定时任务
    # 'send-reminders-every-morning': {
    #     'task': 'booking.tasks.send_reminders',
    #     'schedule': crontab(hour=8, minute=0),
    # }
}