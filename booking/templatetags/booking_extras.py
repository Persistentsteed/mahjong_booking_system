# booking/templatetags/booking_extras.py
import datetime
from django import template
from django.utils import timezone

# 创建一个 Library 实例，所有的标签和过滤器都要注册到这里
register = template.Library()

# 使用 @register.filter 装饰器来定义一个过滤器
# 这个过滤器的作用是从一个字典中根据 key 获取 value
# 这在 Django 模板中非常有用，因为模板语言本身不支持用变量作为 key 来访问字典
@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Usage: {{ my_dictionary|get_item:my_key }}
    """
    if hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None


@register.filter
def get_top_offset(booking, timetable_start_datetime):
    """
    计算预约块距离顶部的像素值 (Top)
    参数: booking (预约对象), timetable_start_datetime (视图传来的 datetime 对象，表示时间轴起点)
    """
    try:
        if not booking or not booking.start_time or not timetable_start_datetime:
            return 0
        
        # 核心：使用视图提供的时间轴起点作为基准
        base_time = timetable_start_datetime
        
        diff = booking.start_time - base_time
        minutes_diff = diff.total_seconds() / 60
        
        # 如果预约开始时间在视图起点之前，则从0px开始显示
        if minutes_diff < 0:
            return 0
        
        return int(minutes_diff)
        
    except Exception as e:
        print(f"Error in get_top_offset: {e}")
        return 0

@register.filter
def get_height_px(booking, timetable_start_datetime): # 也让 height 过滤器接收这个参数
    """
    计算预约块的高度 (Height)
    参数: booking (预约对象), timetable_start_datetime (视图传来的 datetime 对象，表示时间轴起点)
    """
    try:
        if not booking or not booking.start_time or not booking.end_time or not timetable_start_datetime:
            return 0
        
        base_time = timetable_start_datetime
        
        # 视图的结束时间是基准时间 + 24小时
        view_end_time = base_time + datetime.timedelta(hours=24)
        
        # 计算有效显示的时间范围
        effective_start = max(booking.start_time, base_time)
        effective_end = min(booking.end_time, view_end_time)
        
        duration = effective_end - effective_start
        minutes = duration.total_seconds() / 60
        
        return int(max(minutes, 20)) # 最小高度20px，防止太短看不见
    except Exception as e:
        print(f"Error in get_height_px: {e}")
        return 60
    
@register.filter
def timesince_epoch(dt, base_dt):
    """
    计算 dt 距离 base_dt (基准时间) 的总分钟数。用于计算当前时间线的位置。
    如果 dt 或 base_dt 为 None 或不是 datetime 对象，返回 0 防止报错。
    """
    if not dt or not base_dt or not isinstance(dt, datetime.datetime) or not isinstance(base_dt, datetime.datetime):
        return 0
    try:
        diff = dt - base_dt
        return int(max(0, diff.total_seconds() / 60)) # 确保结果非负
    except Exception as e:
        print(f"Error in timesince_epoch filter: {e}")
        return 0 # 出错时返回0
    
@register.filter
def add_minutes(dt, minutes_to_add):
    if not dt or not isinstance(dt, datetime.datetime):
        # 如果 dt 无效，直接返回 None，让后续过滤器处理
        return None 
    try:
        # 确保 minutes_to_add 是数字，如果是 None 或空字符串，默认为0
        minutes_to_add = float(minutes_to_add) if minutes_to_add is not None else 0
        return dt + datetime.timedelta(minutes=minutes_to_add)
    except (ValueError, TypeError):
        # 计算出错，返回 None
        return None

@register.filter
def multiply(value, multiplier):
    if value is None: # 如果 value 是 None，直接返回 None
        return None
    try:
        # 确保 value 和 multiplier 都是数字，如果是 None 或空字符串，默认为0
        value = float(value) if value is not None else 0
        multiplier = float(multiplier) if multiplier is not None else 0
        return value * multiplier
    except (ValueError, TypeError):
        return None

@register.filter
def format_time(dt, format_string):
    if not dt or not isinstance(dt, datetime.datetime):
        # 如果 dt 无效，返回空字符串
        return ""
    return dt.strftime(format_string)