# booking/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Store, Booking
import datetime

# --- 用户认证需要用到的模块 ---
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
# 确保你的 booking/forms.py 里有 SignUpForm
try:
    from .forms import SignUpForm
except ImportError:
    # 如果 forms.py 不存在或没有 SignUpForm，提供一个临时的替代方案
    # 这确保了即使 forms.py 有问题，项目也能运行起来一部分
    from django.contrib.auth.forms import UserCreationForm as SignUpForm

# --- 视图 1: 门店对局情况 (重构) ---
def store_status_view(request):
    stores = Store.objects.prefetch_related('tables').all()
    now = timezone.now()
    
    # --- 核心修正 ---
    # 我们只查询那些 *当前时间* 正好处在 *开始时间* 和 *结束时间* 之间的对局
    current_bookings = Booking.objects.filter(
        status='CONFIRMED',
        table__isnull=False,  # 确保已经分配了牌桌
        start_time__lte=now,  # 对局已经开始
        estimated_end_time__gte=now # 对局尚未结束
    ).select_related('table').prefetch_related('participants')
    
    # 构建一个以 table_id 为键，当前正在进行的预定信息为值的字典
    bookings_by_table = {booking.table.id: booking for booking in current_bookings}

    context = {
        'stores': stores,
        'bookings_by_table': bookings_by_table,
        'now': now,
    }
    return render(request, 'booking/store_status.html', context)

# --- 视图 2: 可加入的预约列表 (全新) ---
def list_pending_bookings_view(request):
    # 只显示未来还未凑齐的局
    pending_bookings = Booking.objects.filter(
        status='PENDING',
        start_time__gte=timezone.now()
    ).prefetch_related('participants')
    
    context = {
        'bookings': pending_bookings
    }
    return render(request, 'booking/list_pending.html', context)

# --- 视图 3: 创建预约 (重构) ---
@login_required
def create_booking_view(request, store_id):
    store = get_object_or_404(Store, id=store_id)
    # 限制每人最多发起2个未成行的局
    if Booking.objects.filter(creator=request.user, status='PENDING').count() >= 2:
        messages.error(request, '您发起的待处理预约已达上限 (2个)。')
        return redirect('store_status')
    
    if request.method == 'POST':
        try:
            start_time_str = request.POST.get('start_time')
            num_games = int(request.POST.get('num_games', 4))
            start_time = timezone.make_aware(datetime.datetime.fromisoformat(start_time_str))

            if start_time < timezone.now() + datetime.timedelta(minutes=30):
                raise ValueError("预约时间必须在30分钟以后。")

            booking = Booking.objects.create(
                creator=request.user,
                store=store,
                start_time=start_time,
                num_games=num_games,
            )
            # 创建者自动加入对局
            booking.participants.add(request.user)
            messages.success(request, '预约已成功发起，等待其他玩家加入！')
            return redirect('my_bookings')
        except (ValueError, TypeError) as e:
            messages.error(request, f'输入有误: {e}')
            return redirect('create_booking', store_id=store_id)

    return render(request, 'booking/create_booking.html', {'store': store})

# --- 视图 4: 加入预约 (全新) ---
@login_required
def join_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, status='PENDING')
    
    if booking.participants.count() >= 4:
        messages.warning(request, '该对局人数已满。')
        return redirect('list_pending_bookings')
        
    if request.user in booking.participants.all():
        messages.warning(request, '您已经加入此对局。')
        return redirect('list_pending_bookings')

    # 将用户加入
    booking.participants.add(request.user)
    
    # 自动匹配逻辑：如果人数达到4人
    if booking.participants.count() == 4:
        booking.status = 'CONFIRMED'
        booking.save()
        # 在这里可以添加通知逻辑，通知所有参与者
        messages.success(request, '加入成功！此对局已满4人，成功成行！')
        # TODO: 未来还可以加入自动分配牌桌的逻辑
    else:
        messages.success(request, '成功加入对局！')

    return redirect('list_pending_bookings')

# --- 视图 5: 取消/退出预约 (全新) ---
@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    user = request.user
    
    # 确认用户是参与者之一
    if user not in booking.participants.all():
        messages.error(request, '您没有权限执行此操作。')
        return redirect('my_bookings')

    # 逻辑 1: 取消未成行的局 (PENDING)
    if booking.status == 'PENDING':
        booking.participants.remove(user)
        # 如果退出后没人了，直接删除这个预约
        if booking.participants.count() == 0:
            booking.delete()
            messages.success(request, '您已退出且该预约已自动取消。')
        else:
            # 如果退出的是创建者，需要重新指定一个创建者（或者简单地保留原创建者信息）
            # 这里我们简单保留
            messages.success(request, '您已成功退出该预约。')
        return redirect('my_bookings')
        
    # 逻辑 2: 取消已成行的局 (CONFIRMED)
    if booking.status == 'CONFIRMED':
        # 检查是否在开始前1小时以上
        if booking.start_time > timezone.now() + datetime.timedelta(hours=1):
            booking.participants.remove(user)
            # 状态退回 PENDING，让其他人可以再次加入
            booking.status = 'PENDING'
            booking.save()
            messages.success(request, '您已退出对局，该对局现在重新开放让他人加入。')
            # 在这里可以添加通知逻辑，通知其他三位参与者有人退出
        else:
            messages.error(request, '已成行的对局必须在开始前1小时以上才能取消。')
        return redirect('my_bookings')

    messages.warning(request, '该对局状态已无法取消。')
    return redirect('my_bookings')

# --- 视图 6: 我的预约 (重构) ---
@login_required
def my_bookings_view(request):
    # joined_bookings 是我们在 User 模型中通过 related_name 定义的
    bookings = request.user.joined_bookings.all().order_by('start_time')
    return render(request, 'booking/my_bookings.html', {'bookings': bookings})

# --- 用户认证视图 (保持不变) ---
def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('store_status')
    else:
        form = SignUpForm()
    return render(request, 'booking/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('store_status')
    else:
        form = AuthenticationForm()
    return render(request, 'booking/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('store_status')