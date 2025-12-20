# booking/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking

@shared_task
def cleanup_expired_bookings():
    expiration_time = timezone.now() - timedelta(hours=24)
    
    expired_bookings = Booking.objects.filter(
        status='PENDING',
        created_at__lt=expiration_time
    )
    
    count = expired_bookings.count()
    if count > 0:
        expired_bookings.update(status='CANCELED')
    
    # 自动删除已结束但未成行的记录
    auto_deleted = Booking.objects.filter(
        status='PENDING',
        end_time__lt=timezone.now()
    )
    deleted_count = auto_deleted.count()
    if deleted_count:
        auto_deleted.delete()
    
    if count or deleted_count:
        return f"标记过期 {count} 条，删除已截止未成行 {deleted_count} 条。"
    return "没有发现需要清理的预约。"
