# booking/admin.py

from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from django.conf import settings # 引入 settings，用于引用 AUTH_USER_MODEL
from .models import Store, MahjongTable, Booking
# 导入我们自定义的用户模型，以便在自定义表单中使用
# 如果你在 accounts 应用中定义了 CustomUser，请确保 CustomUser 可用
# from accounts.models import CustomUser 

# 获取当前使用的用户模型
# 使用 settings.AUTH_USER_MODEL 比直接导入具体的 User 模型更灵活，
# 因为它会根据 AUTH_USER_MODEL 配置动态获取用户模型。
# 但对于 admin.py 中的直接引用，为了类型提示和明晰，如果 CustomUser 已定义，导入它也是可以的。
# 这里我们继续使用 settings.AUTH_USER_MODEL 的方式，因为它已在 Booking 模型中正确引用。

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    """
    门店模型后台管理
    """
    list_display = ('name', 'address')

@admin.register(MahjongTable)
class MahjongTableAdmin(admin.ModelAdmin):
    """
    麻将桌模型后台管理
    """
    list_display = ('table_number', 'store', 'get_current_status')
    list_filter = ('store',)
    actions = ['create_walk_in_booking'] # 管理员操作：创建散客对局

    def create_walk_in_booking(self, request, queryset):
        """
        Admin Action: 为选中的单个牌桌创建散客对局
        """
        if queryset.count() != 1:
            self.message_user(request, "请一次只选择一个牌桌进行此操作。", level='WARNING')
            return

        table = queryset.first()
        now = timezone.now()

        # 检查该桌当前是否已被占用
        if Booking.objects.filter(table=table, status='CONFIRMED', end_time__gt=now).exists():
            self.message_user(request, f"{table} 当前已被占用，无法创建新的对局。", level='ERROR')
            return

        # 创建一个默认的散客对局
        Booking.objects.create(
            creator=request.user,  # 使用当前管理员作为 creator
            store=table.store,
            table=table,
            start_time=now,
            num_games=4,           # 默认4个半庄
            booking_type='GAMES',  # 明确指定预约类型为按半庄数
            status='CONFIRMED',    # 直接设置为已成行
            # end_time 会在 Booking 模型的 save 方法中根据 num_games 自动计算
        )
        self.message_user(request, f"已为 {table} 成功创建一个为期3小时的散客对局。")

    create_walk_in_booking.short_description = "为选中牌桌创建散客对局 (占用3小时)"

    def get_current_status(self, obj):
        """
        辅助方法: 获取牌桌的当前占用状态
        """
        now = timezone.now()
        if Booking.objects.filter(table=obj, status='CONFIRMED', end_time__gt=now).exists():
            return "占用中"
        return "空闲"
    get_current_status.short_description = "当前状态"

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    对局预约模型后台管理
    """
    # list_display 中 'creator' 会显示 CustomUser 的 __str__ 定义（优先 display_name，否则 username）
    list_display = ('creator', 'store', 'booking_type', 'start_time', 'end_time', 'status', 'get_participant_count', 'table')
    list_filter = ('status', 'store', 'booking_type', 'start_time')
    # 搜索字段增加 creator 的 display_name，以支持中文搜索
    search_fields = ('creator__username', 'creator__display_name', 'store__name')
    
    # --- 修复 1: 确保参与者、半庄数和结束时间在自定义表单中是非必填项 ---
    def get_form(self, request, obj=None, **kwargs):
        """
        自定义 ModelForm，修改字段的必填属性
        """
        form = super().get_form(request, obj, **kwargs)
        # 参与者(ManyToManyField)在创建时可为空
        if 'participants' in form.base_fields:
            form.base_fields['participants'].required = False
        
        # num_games 和 end_time 也是在不同 booking_type 下互斥的，设为非必填
        if 'num_games' in form.base_fields:
            form.base_fields['num_games'].required = False
        if 'end_time' in form.base_fields:
            form.base_fields['end_time'].required = False
            
        return form

    # --- 核心改动 1: 动态显示和编辑字段 ---
    def get_fieldsets(self, request, obj=None):
        """
        根据对象状态和预约类型动态决定显示哪些字段
        """
        fieldsets = []
        
        # 创建新预约时的字段布局
        if obj is None:
            fieldsets.append(('基本信息', {
                'fields': ('creator', 'store', 'booking_type', 'status', 'start_time', 'end_time', 'num_games')
            }))
            fieldsets.append(('参与者', {'fields': ('participants',)}))
        # 编辑现有预约时的字段布局
        else:
            # 基础信息：creator, store, booking_type, status, start_time
            base_info_fields = ['creator', 'store', 'booking_type', 'status', 'start_time']
            
            # 根据预约类型动态添加 num_games 或 end_time
            if obj.booking_type == 'GAMES':
                base_info_fields.append('num_games')
            else: # DURATION 类型
                base_info_fields.append('end_time') # end_time 字段已在 Booking 模型中明确定义

            fieldsets.append(('基本信息', {'fields': tuple(base_info_fields)}))
            fieldsets.append(('参与者', {'fields': ('participants', 'table')})) # table 字段移到这里作为默认显示，若 CONFIRMED 再展开

            # 如果对局已成行，且尚未分配牌桌，则额外显示“牌桌分配”区域
            if obj.status == 'CONFIRMED' and not obj.table: # 只有状态为 CONFIRMED 且尚未分配牌桌才显示
                 fieldsets.append(
                     ('牌桌分配 (仅对已成行对局)', {
                         'fields': ('table',),
                     })
                 )

        return fieldsets

    # --- 修复 2: 优化 get_readonly_fields 逻辑以支持 num_games/end_time 动态编辑 ---
    def get_readonly_fields(self, request, obj=None):
        """
        动态设置只读字段。
        注意：M2M 字段 (participants) 不直接在此列出，其可编辑性在 get_form 中控制。
        """
        read_only_fields = ['created_at'] # 创建时间始终只读

        if obj: # 如果是编辑现有对象
            # 一旦创建，这些核心属性通常不应再更改
            # 如果需要更改，应该取消重新预约，保持数据完整性
            read_only_fields.extend(['creator', 'booking_type', 'start_time']) 
            
            # 根据预约类型，动态设置另一个时间/数量字段的只读
            if obj.booking_type == 'GAMES':
                read_only_fields.append('end_time') # 按半庄数则 end_time 自动计算，只读
            else: # DURATION 类型
                read_only_fields.append('num_games') # 按时间段则 num_games 不参与，只读

        return tuple(read_only_fields)

    # --- 核心改动 2: 筛选出可分配的牌桌 ---
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        自定义外键字段的下拉选项（比如为牌桌字段提供筛选）。
        """
        if db_field.name == "table":
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                booking = self.get_object(request, obj_id)
                if booking: # 确保 booking 对象存在
                    # 找出在当前 booking 时间段内已被占用的桌子ID
                    conflicting_bookings = Booking.objects.filter(
                        store=booking.store,
                        status='CONFIRMED',
                        table__isnull=False,
                        # 检查时间段冲突：已分配的预约其时间段与当前预约有重叠
                        start_time__lt=booking.end_time,
                        end_time__gt=booking.start_time
                    ).exclude(pk=booking.pk) # 排除当前正在编辑的预约本身
                        
                    occupied_table_ids = conflicting_bookings.values_list('table_id', flat=True)
                    
                    # 筛选出同门店下，且当前时间段内空闲的桌子
                    kwargs["queryset"] = MahjongTable.objects.filter(
                        store=booking.store
                    ).exclude(id__in=occupied_table_ids)
            else: # 如果是创建新预约，默认显示所有桌子
                kwargs["queryset"] = MahjongTable.objects.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)     
      
    # 辅助方法：计算参与人数并显示
    def get_participant_count(self, obj):     
        return obj.participants.count()     
    get_participant_count.short_description = '参与人数'     
    
    # --- 核心改动 3: 提供一个快速成局的 Action ---
    actions = ['confirm_selected_bookings']     
    
    def confirm_selected_bookings(self, request, queryset):     
        """
        Admin Action: 将选中的满足条件的预约标记为 '已成行'。
        """
        valid_bookings = queryset.filter(status='PENDING').annotate(p_count=Count('participants')).filter(p_count=4)     
            
        if valid_bookings:     
            updated_count = valid_bookings.update(status='CONFIRMED')     
            self.message_user(request, f"{updated_count} 个满足条件的预约已成功标记为 '已成行'。", level='SUCCESS')     
        else:     
            self.message_user(request, "选中的预约中没有满足成行条件（等待中且满员）的。", level='WARNING')     
        
    confirm_selected_bookings.short_description = "将选中项标记为 '已成行' (仅限满员)"