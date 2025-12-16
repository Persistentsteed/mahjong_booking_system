# booking/models.py

from django.db import models
from django.conf import settings
User = settings.AUTH_USER_MODEL 
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
    # --- 预约类型 ---
    BOOKING_TYPE_CHOICES = [
        ('GAMES', '按半庄数'),
        ('DURATION', '按时间段'),
    ]
    booking_type = models.CharField(
        max_length=10,
        choices=BOOKING_TYPE_CHOICES,
        default='GAMES',
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
        # 如果是按半庄数预约，并且 end_time 为空（即没有手动指定时间段）
        # 那么根据半庄数自动计算 end_time
        if not self.start_time:
        # 这应该通过表单验证来避免，但这里做个兜底
            self.start_time = timezone.now() 
    
        # 确保 num_games 始终有值，即使为 0
        if self.booking_type == 'GAMES' and self.num_games is None:
            self.num_games = 0

        if self.end_time is None:
            if self.booking_type == 'GAMES' and self.num_games is not None:
                duration_minutes = self.num_games * 45
                self.end_time = self.start_time + datetime.timedelta(minutes=duration_minutes)
            elif self.booking_type == 'DURATION':
                # 如果是 DURATION 类型，但 end_time 还是 None，说明用户可能没填或出错
                # 再次强调，这应该由表单/视图前端验证，这里做个兜底
                self.end_time = self.start_time + datetime.timedelta(hours=1) # 默认1小时后结束
            else:
                # 既不是 GAMES 也不是 DURATION，或 num_games 无效，给个默认时长
                self.end_time = self.start_time + datetime.timedelta(hours=1)
        
        super().save(*args, **kwargs)

    # --- 更新 __str__ 方法，使其更具可读性 ---
    def __str__(self):
        return f"{self.creator.username} 在 {self.store.name} 发起的对局 ({self.get_status_display()})"

    # --- 新增属性，方便模板中直接调用计算时长 ---
    @property
    def display_end_time(self):
        if self.booking_type == 'GAMES' and self.num_games is not None:
            # 在这里计算预计结束时间，确保是带时区信息的
            # 因为 self.start_time 已经是带时区信息的了
            return self.start_time + datetime.timedelta(minutes=self.num_games * 45)
        return self.end_time # 按时段预约则直接返回 end_time
    class Meta:
        verbose_name = "对局预约"
        verbose_name_plural = verbose_name
        ordering = ['start_time'] # 默认按开始时间排序