# booking/models.py

from django.db import models
from django.contrib.auth.models import User # 导入Django内置的用户模型
from django.utils import timezone
import datetime

# 1. 门店模型
class Store(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="门店名称")
    address = models.CharField(max_length=255, verbose_name="门店地址")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "门店"
        verbose_name_plural = verbose_name

# 2. 麻将桌模型
class MahjongTable(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='tables', verbose_name="所属门店")
    table_number = models.CharField(max_length=20, verbose_name="桌号")
    
    class Meta:
        unique_together = ('store', 'table_number')
        verbose_name = "麻将桌"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.store.name} - {self.table_number}"

# 3. 预约/对局记录模型
class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', '匹配中'),
        ('CONFIRMED', '匹配成功'),
        ('CANCELED', '已取消'),
        ('EXPIRED', '已过期'),
        ('COMPLETED', '已完成'),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_bookings', verbose_name="发起人")
    participants = models.ManyToManyField(User, related_name='joined_bookings', verbose_name="参与者")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="预约门店")
    table = models.ForeignKey(MahjongTable, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="安排牌桌")
    
    start_time = models.DateTimeField(verbose_name="预计开始时间")
    num_games = models.PositiveIntegerField(default=4, verbose_name="预计局数 (半庄)")

    # 这个字段由 save 方法自动计算，不在表单中显示
    estimated_end_time = models.DateTimeField(verbose_name="预计结束时间", editable=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="预约状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def save(self, *args, **kwargs):
        # 假设一个半庄平均耗时45分钟
        duration_minutes = self.num_games * 45
        self.estimated_end_time = self.start_time + datetime.timedelta(minutes=duration_minutes)
        super().save(*args, **kwargs)

def __str__(self):
    return f"{self.creator.username} 在 {self.store.name} 发起的对局 ({self.get_status_display()})"

    class Meta:
        verbose_name = "对局预约"
        verbose_name_plural = verbose_name
        ordering = ['start_time'] # 默认按开始时间排序