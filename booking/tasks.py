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
        expired_bookings.update(status='EXPIRED')
        return f"成功清理 {count} 条过期预约。"
    return "没有发现过期预约。"