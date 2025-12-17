# booking/models.py

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
User = settings.AUTH_USER_MODEL 
from django.utils import timezone
import datetime
import math

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
    alias = models.CharField(max_length=50, blank=True, null=True, verbose_name="别名/位置描述")
    
    class Meta:
        unique_together = ('store', 'table_number')
        verbose_name = "麻将桌"
        verbose_name_plural = verbose_name

    def display_label(self):
        if self.alias:
            return f"{self.table_number} - {self.alias}"
        return self.table_number

    def __str__(self):
        return self.display_label()

# 3. 预约/对局记录模型
class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', '匹配中'),
        ('CONFIRMED', '匹配成功'),
        ('CANCELED', '已取消'),
        ('EXPIRED', '已过期'),
        ('COMPLETED', '已完成'),
    ]
    # --- 预约类型 ---
    BOOKING_TYPE_CHOICES = [
        ('STANDARD', '标准预约'),
    ]
    booking_type = models.CharField(
        max_length=10,
        choices=BOOKING_TYPE_CHOICES,
        default='STANDARD',
        verbose_name="预约类型"
    )

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_bookings', verbose_name="发起人")
    participants = models.ManyToManyField(User, related_name='joined_bookings', verbose_name="参与者")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, verbose_name="预约门店")
    table = models.ForeignKey(MahjongTable, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="安排牌桌")
    
    start_time = models.DateTimeField(verbose_name="预计开始时间")
    num_games = models.PositiveIntegerField(
        default=4,
        verbose_name="半庄数",
        null=True,  # 允许数据库中该字段为 NULL
        blank=True  # 允许在表单中不填写该字段
    )
    end_time = models.DateTimeField(verbose_name="结束时间")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', verbose_name="预约状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    # --- 重写 save 方法以适应新逻辑 ---
    def save(self, *args, **kwargs):
        # 1. 确保 start_time 存在
        if not self.start_time:
           self.start_time = timezone.now() # 兜底，但最好在表单/视图层进行更严格的验证和错误提示

        # 2. 统一保存逻辑：若缺少结束时间则按半庄数推算；若缺少半庄数则由时间推算
        if self.end_time is None and self.num_games:
            duration_minutes = self.num_games * 45
            self.end_time = self.start_time + datetime.timedelta(minutes=duration_minutes)

        if self.num_games in (None, 0) and self.end_time:
            duration = self.end_time - self.start_time
            minutes = max(duration.total_seconds() / 60, 45)
            self.num_games = max(1, math.ceil(minutes / 45))

        # 3. 如果 end_time 仍然为空，兜底1小时
        if self.end_time is None:
            self.end_time = self.start_time + datetime.timedelta(hours=1)

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.table and self.store and self.table.store_id != self.store_id:
            raise ValidationError({'table': "所选牌桌不属于当前门店，请重新选择。"})

    # --- 更新 __str__ 方法，使其更具可读性 ---
    def __str__(self):
        return f"{self.creator.username} 在 {self.store.name} 发起的对局 ({self.get_status_display()})"

    # --- 新增属性，方便模板中直接调用计算时长 ---
    @property
    def display_end_time(self):
        if self.num_games is not None:
            return self.start_time + datetime.timedelta(minutes=self.num_games * 45)
        return self.end_time # 按时段预约则直接返回 end_time
    class Meta:
        verbose_name = "对局预约"
        verbose_name_plural = verbose_name
        ordering = ['start_time'] # 默认按开始时间排序
