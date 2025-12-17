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
        # 1. 确保 start_time 存在
        if not self.start_time:
           self.start_time = timezone.now() # 兜底，但最好在表单/视图层进行更严格的验证和错误提示

        # 2. 只有当 end_time 尚未被明确设定时，才进行自动计算/默认值设定
        # 如果用户在前端或视图中已经给 self.end_time 赋值了，这里就不动它
        if self.end_time is None:
            if self.booking_type == 'GAMES':
                # 如果是 GAMES 类型，检查 num_games
                if self.num_games is not None and self.num_games >= 0:
                    duration_minutes = self.num_games * 45
                    self.end_time = self.start_time + datetime.timedelta(minutes=duration_minutes)
                else:
                    # 如果 num_games 无效，给一个默认时长，避免 end_time 为 None
                    self.end_time = self.start_time + datetime.timedelta(hours=1) 
            elif self.booking_type == 'DURATION':
                # DURATION 类型如果 end_time 仍是 None，说明用户可能没填，给个默认值
                self.end_time = self.start_time + datetime.timedelta(hours=1)
            else:
                # 未知类型，也给个默认时长
                self.end_time = self.start_time + datetime.timedelta(hours=1)
            
        # 3. 如果 end_time 仍然是 None（理论上不会，但做个双重检查）
        # 且 start_time 有效，给个默认值
        if self.end_time is None and self.start_time is not None:
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