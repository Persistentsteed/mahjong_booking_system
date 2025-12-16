# booking/admin.py

from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from .models import Store, MahjongTable, Booking

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')

@admin.register(MahjongTable)
class MahjongTableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'store', 'get_current_status')
    list_filter = ('store',)
    
    # --- 新增功能 ---
    actions = ['create_walk_in_booking']

    def create_walk_in_booking(self, request, queryset):
        # 这个 action 只应该对一个桌子操作
        if queryset.count() != 1:
            self.message_user(request, "请一次只选择一个牌桌进行此操作。", level='WARNING')
            return

        table = queryset.first()
        now = timezone.now()

        # 检查该桌当前是否空闲
        if Booking.objects.filter(table=table, status='CONFIRMED', estimated_end_time__gt=now).exists():
            self.message_user(request, f"{table} 当前已被占用，无法创建新的对局。", level='ERROR')
            return

        # 创建一个匿名的“散客”用户或使用一个固定的系统用户
        # 这里我们简单地使用发起请求的管理员作为创建者
        
        # 创建一个默认的散客对局，例如持续4个半庄 (3小时)
        Booking.objects.create(
            creator=request.user, # 用当前管理员作为发起人
            store=table.store,
            table=table,
            start_time=now,
            num_games=4, # 默认4个半庄
            status='CONFIRMED' # 直接设置为已成行
        )
        self.message_user(request, f"已为 {table} 成功创建一个为期3小时的散客对局。")

    create_walk_in_booking.short_description = "为选中牌桌创建散客对局 (占用3小时)"

    def get_current_status(self, obj):
        now = timezone.now()
        if Booking.objects.filter(table=obj, status='CONFIRMED', estimated_end_time__gt=now).exists():
            return "占用中"
        return "空闲"
    get_current_status.short_description = "当前状态"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('creator', 'store', 'start_time', 'status', 'get_participant_count', 'table')
    list_filter = ('status', 'store', 'start_time')
    search_fields = ('creator__username', 'store__name')
    
    # --- 核心改动 1: 动态显示和编辑字段 ---
    def get_fieldsets(self, request, obj=None):
        """根据对象状态动态决定显示哪些字段"""
        base_fields = ('creator', 'store', 'status', 'start_time', 'num_games')
        participants_fields = ('participants',)
        
        # 默认的字段布局
        fieldsets = [
            ('基本信息', {'fields': base_fields}),
            ('参与者', {'fields': participants_fields, 'classes': ('collapse',)}),
        ]

        # 如果对局已成行，则额外显示“牌桌分配”区域
        if obj and obj.status == 'CONFIRMED':
            fieldsets.append(
                ('牌桌分配 (仅对已成行对局)', {
                    'fields': ('table',),
                })
            )
        
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        """让参与者列表在编辑时只读，防止误操作"""
        return ('participants',)

    # --- 核心改动 2: 筛选出可分配的牌桌 ---
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # 当编辑 'table' 字段时
        if db_field.name == "table":
            # 获取当前正在编辑的 booking 对象
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                booking = self.get_object(request, obj_id)
                # 筛选出与该 booking 同一个门店的、并且在时间段内空闲的桌子
                # 注意：这是一个简化的冲突检测，只考虑了已分配桌位的CONFIRMED对局
                
                # 找出在当前 booking 时间段内已被占用的桌子ID
                conflicting_bookings = Booking.objects.filter(
                    store=booking.store,
                    status='CONFIRMED',
                    table__isnull=False,
                    start_time__lt=booking.estimated_end_time,
                    estimated_end_time__gt=booking.start_time
                ).exclude(pk=booking.pk) # 排除自己
                
                occupied_table_ids = conflicting_bookings.values_list('table_id', flat=True)
                
                # 将 queryset 限制为同门店下，且不在被占用列表中的桌子
                kwargs["queryset"] = MahjongTable.objects.filter(
                    store=booking.store
                ).exclude(id__in=occupied_table_ids)
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_participant_count(self, obj):
        return obj.participants.count()
    get_participant_count.short_description = '参与人数'

    # --- 核心改动 3: 提供一个快速成局的 Action ---
    actions = ['confirm_selected_bookings']

    def confirm_selected_bookings(self, request, queryset):
        # 筛选出状态是 PENDING 且人数已满的
        valid_bookings = queryset.filter(status='PENDING').annotate(p_count=Count('participants')).filter(p_count=4)
        
        if valid_bookings:
            updated_count = valid_bookings.update(status='CONFIRMED')
            self.message_user(request, f"{updated_count} 个满足条件的预约已成功标记为 '已成行'。")
        else:
            self.message_user(request, "选中的预约中没有满足成行条件（等待中且满员）的。", level='WARNING')
    
    confirm_selected_bookings.short_description = "将选中项标记为 '已成行' (仅限满员)"