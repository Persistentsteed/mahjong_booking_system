# config/urls.py

from django.contrib import admin
# 确保你导入了 `path` 和 `include`
from django.urls import path, include 

urlpatterns = [
    # 将 /admin/ 的所有请求交给 Django admin 应用处理
    path('admin/', admin.site.urls),
    
    # 将所有其他的请求 (路径前缀为空 '') 交给 'booking.urls' 去处理
    # 这才是正确的做法！
    path('', include('booking.urls')), 
]