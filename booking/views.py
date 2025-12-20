# booking/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Store, Booking
from accounts.forms import CustomUserCreationForm
from django.db.models import Q 
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
    for store in stores:
        store.sorted_tables = store.tables.all().order_by('table_number')
    now = timezone.now()
    
    # --- 核心修正 ---
    # 我们只查询那些 *当前时间* 正好处在 *开始时间* 和 *结束时间* 之间的对局
    current_bookings = Booking.objects.filter(
        status='CONFIRMED',
        table__isnull=False,  # 确保已经分配了牌桌
        start_time__lte=now,  # 对局已经开始
        end_time__gte=now # 对局尚未结束
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
    pending_bookings = Booking.objects.filter(
        status='PENDING',
        end_time__gte=timezone.now()  # 或者 Q(end_time__gte=timezone.now()) | Q(start_time__gte=timezone.now())
    ).prefetch_related('participants')
    
    pending_bookings = list(pending_bookings)
    last_hour = timezone.now() + datetime.timedelta(hours=1)
    for booking in pending_bookings:
        booking.is_last_hour = booking.start_time <= last_hour
    
    context = {
        'bookings': pending_bookings
    }
    return render(request, 'booking/list_pending.html', context)

# --- 视图 3: 创建预约 (重构) ---
@login_required
def create_booking_view(request, store_id):
    store = get_object_or_404(Store, id=store_id)
    
    if Booking.objects.filter(
        creator=request.user,
        status='PENDING',
        end_time__gte=timezone.now()
    ).count() >= 2:
        messages.error(request, '您发起的待处理预约已达上限 (2个)。')
        return redirect('store_status')
    
    if request.method == 'POST':
        try:
            start_time_str = request.POST.get('start_time')
            end_time_str = request.POST.get('end_time')
            num_games = int(request.POST.get('num_games', 0))

            if not start_time_str or not end_time_str:
                raise ValueError("请填写开始与结束时间。")
            if num_games <= 0:
                raise ValueError("半庄数必须大于0。")

            start_time = timezone.make_aware(datetime.datetime.fromisoformat(start_time_str))
            end_time = timezone.make_aware(datetime.datetime.fromisoformat(end_time_str))

            if end_time <= start_time:
                raise ValueError("结束时间必须晚于开始时间。")

            overlapping_confirmed = request.user.joined_bookings.filter(
                status='CONFIRMED',
                end_time__gt=start_time,
                start_time__lt=end_time,
            )

            if overlapping_confirmed.exists():
                messages.error(request, '该时间段内您已有已成行对局，无法重复预约。')
                return redirect('create_booking', store_id=store_id)

            booking = Booking(
                creator=request.user,
                store=store,
                start_time=start_time,
                end_time=end_time,
                num_games=num_games,
            )

            booking.save()
            booking.participants.add(request.user)
            messages.success(request, '预约已成功发起！')
            return redirect('my_bookings')

        except (ValueError, TypeError) as e:
            messages.error(request, f'输入有误: {e}')
            # 渲染回表单，保留已填数据（可选，这里只是简单重定向）
            return redirect('create_booking', store_id=store_id)
            
    # GET 请求时渲染表单 (保持不变)
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
    bookings = (
        request.user.joined_bookings
        .filter(
            end_time__gte=timezone.now(),
            status__in=['PENDING', 'CONFIRMED']
        )
        .select_related('store', 'table')
        .prefetch_related('participants')
        .order_by('start_time')
    )
    return render(request, 'booking/my_bookings.html', {'bookings': bookings})


@login_required
def my_games_view(request):
    games_qs = (
        request.user.joined_bookings
        .filter(status='CONFIRMED')
        .select_related('store', 'table')
        .prefetch_related('participants')
        .order_by('-start_time')
    )
    games = list(games_qs)

    phase_counts = {'NOT_STARTED': 0, 'IN_PROGRESS': 0, 'COMPLETED': 0}
    for game in games:
        phase = game.game_phase
        if phase in phase_counts:
            phase_counts[phase] += 1

    context = {
        'games': games,
        'phase_counts': phase_counts,
    }
    return render(request, 'booking/my_games.html', context)


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST) # 使用新的表单
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('store_status')
    else:
        form = CustomUserCreationForm()
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

def store_timetable_view(request, store_id):
    store = get_object_or_404(Store, id=store_id)
    local_timezone = timezone.get_current_timezone() # 获取 settings.TIME_ZONE
    now = timezone.localtime(timezone.now()) # 将当前 UTC 时间转换为本地时区时间
    
    # 确定视图展示的24小时的起始时间
    # 为了让视图从整点开始，我们可以选择当前小时的整点作为开始
    # 或者从某一天的0点开始，这里为了简单，我们还是从当前小时整点开始，更符合“实时”
    start_of_view = now.replace(minute=0, second=0, microsecond=0)
    end_of_view = start_of_view + datetime.timedelta(hours=24)

    # 确保时间轴的起始时间也是这一天/小时
    timeline_start_display_hour = start_of_view.hour

    bookings = Booking.objects.filter(
        store=store,
        status='CONFIRMED',
        table__isnull=False,
        # 过滤条件：预约的结束时间晚于视图开始时间 且 预约的开始时间早于视图结束时间
        end_time__gt=start_of_view,
        start_time__lt=end_of_view
    ).select_related('table', 'creator')
    
    bookings_by_table = {table.id: [] for table in store.tables.all()}
    for booking in bookings:
        if booking.table:
            bookings_by_table[booking.table.id].append(booking)

    time_slots = []
    for i in range(24): # 24个时间格
        slot_time = start_of_view + datetime.timedelta(hours=i)
        time_slots.append({
            'label': slot_time.strftime('%H:00'),
            'is_current_hour': (slot_time.hour == now.hour and slot_time.day == now.day) # 标记当前小时
        })

    context = {
        'store': store,
        'bookings_by_table': bookings_by_table,
        'tables': store.tables.all().order_by('table_number'),
        'time_slots': time_slots,
        'timetable_start_datetime': start_of_view, # 将完整的 datetime 对象传递过去
        'timeline_start_display_hour': timeline_start_display_hour, # 用于在标题显示范围
        'now': now, # 用于画当前时间线

    }
    return render(request, 'booking/store_timetable.html', context)
