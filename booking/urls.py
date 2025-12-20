# booking/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 核心页面
    path('', views.store_status_view, name='store_status'),
    path('pending-bookings/', views.list_pending_bookings_view, name='list_pending_bookings'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('my-games/', views.my_games_view, name='my_games'),
    
    # 操作 URL
    path('book/create/<int:store_id>/', views.create_booking_view, name='create_booking'),
    path('book/join/<int:booking_id>/', views.join_booking_view, name='join_booking'),
    path('book/cancel/<int:booking_id>/', views.cancel_booking_view, name='cancel_booking'),
    
    # 用户认证
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('store/<int:store_id>/timetable/', views.store_timetable_view, name='store_timetable'),
]
