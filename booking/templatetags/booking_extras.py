# booking/templatetags/booking_extras.py

from django import template

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