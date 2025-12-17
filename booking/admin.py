# booking/admin.py

from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from django.conf import settings 
from django import forms
from django.contrib.admin.helpers import ActionForm
import datetime
# 从 accounts.models 导入 CustomUser（确保路径正确）
from accounts.models import CustomUser 
from .models import Store, MahjongTable, Booking

# 新增导入：处理 HTTP 响应和 Excel 文件
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

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
            # ★★★ 修复：将 _self_ 改为 self ★★★
            self.message_user(request, "请一次只选择一个牌桌进行此操作。", level='WARNING')
            return

        table = queryset.first()
        now = timezone.now()

        # 检查该桌当前是否已被占用
        if Booking.objects.filter(table=table, status='CONFIRMED', end_time__gt=now).exists():
            # ★★★ 修复：将 _self_ 改为 self ★★★
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
        # ★★★ 修复：将 _self_ 改为 self ★★★
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

class BookingExportActionForm(ActionForm):
    start_date = forms.DateField(
        required=False,
        label="开始日期",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    end_date = forms.DateField(
        required=False,
        label="结束日期",
        widget=forms.DateInput(attrs={"type": "date"})
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    对局预约模型后台管理
    """
    list_display = ('creator', 'store', 'booking_type', 'start_time', 'end_time', 'status', 'get_participant_count', 'table')
    list_filter = ('status', 'store', 'booking_type', 'start_time')
    search_fields = ('creator__username', 'creator__display_name', 'store__name')
    autocomplete_fields = ['creator', 'participants'] 
    action_form = BookingExportActionForm
    
    # --- 修复 1: 确保参与者、半庄数和结束时间在自定义表单中是非必填项 ---
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'participants' in form.base_fields:
            form.base_fields['participants'].required = False
        
        # num_games 和 end_time 也是在不同 booking_type 下互斥的，设为非必填
        if 'num_games' in form.base_fields:
            form.base_fields['num_games'].required = False
        if 'end_time' in form.base_fields:
            form.base_fields['end_time'].required = False
            
        return form
    
    # --- 辅助方法：计算参与人数并显示 (与修复无关，保持不变) ---
    def get_participant_count(self, obj):     
        return obj.participants.count()     
    get_participant_count.short_description = '参与人数'       
  
    # --- 管理员 Actions ---
    actions = ['confirm_selected_bookings', 'export_bookings_to_xlsx', 'export_schedule_to_xlsx'] # 在这里添加新的 Action

    def confirm_selected_bookings(self, request, queryset):       
        valid_bookings = queryset.filter(status='PENDING').annotate(p_count=Count('participants')).filter(p_count=4)       
              
        if valid_bookings:       
            updated_count = valid_bookings.update(status='CONFIRMED')       
            # ★★★ 修复：将 _self_ 改为 self ★★★
            self.message_user(request, f"{updated_count} 个满足条件的预约已成功标记为 '已成行'。", level='SUCCESS')     
        else:       
            # ★★★ 修复：将 _self_ 改为 self ★★★
            self.message_user(request, "选中的预约中没有满足成行条件（等待中且满员）的。", level='WARNING')       
          
    confirm_selected_bookings.short_description = "将选中项标记为 '已成行' (仅限满员)"   

    def _filter_queryset_by_dates(self, request, queryset):
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        start_dt = None
        end_dt = None
        if start_date_str:
            try:
                start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
                start_dt = timezone.make_aware(datetime.datetime.combine(start_dt.date(), datetime.time.min))
            except ValueError:
                self.message_user(request, "开始日期格式错误。", level='ERROR')
        if end_date_str:
            try:
                end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
                end_dt = timezone.make_aware(datetime.datetime.combine(end_dt.date(), datetime.time.max))
            except ValueError:
                self.message_user(request, "结束日期格式错误。", level='ERROR')
        if start_dt:
            queryset = queryset.filter(start_time__gte=start_dt)
        if end_dt:
            queryset = queryset.filter(start_time__lte=end_dt)
        return queryset, start_dt, end_dt

    def export_bookings_to_xlsx(self, request, queryset):   
        """   
        Admin Action: 导出选中的对局记录为 XLSX 文件  
        """   
        queryset, start_dt, end_dt = self._filter_queryset_by_dates(request, queryset)
        response = HttpResponse(   
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'   
        )   
        response['Content-Disposition'] = 'attachment; filename="mahjong_bookings_export.xlsx"'   
  
        workbook = Workbook()   
        worksheet = workbook.active  
        worksheet.title = "对局记录"   
  
        # 定义表头  
        columns = [   
            ("ID", 5),   
            ("发起人", 15),   
            ("参与者", 30), # 参与者可能较多，宽度大一些  
            ("门店", 15),   
            ("牌桌", 10),   
            ("预约类型", 10),   
            ("半庄数", 8),   
            ("开始时间", 20),   
            ("结束时间", 20),   
            ("状态", 10),   
            ("创建时间", 20),   
        ]   
          
        header_font = Font(name='Calibri', bold=True)   
        thin_border = Border(left=Side(style='thin'),   
                             right=Side(style='thin'),   
                             top=Side(style='thin'),   
                             bottom=Side(style='thin'))   
        align_center = Alignment(horizontal="center", vertical="center")   
        align_left = Alignment(horizontal="left", vertical="top", wrap_text=True)   
  
  
        # 写入表头  
        for col_idx, (header_text, width) in enumerate(columns, 1):   
            cell = worksheet.cell(row=1, column=col_idx, value=header_text)   
            cell.font = header_font  
            cell.alignment = align_center  
            cell.border = thin_border  
            worksheet.column_dimensions[get_column_letter(col_idx)].width = width  
          
        row_num = 2  
        for booking in queryset.order_by('start_time'):   
            participants_str = ", ".join([p.display_name or p.username for p in booking.participants.all()])   
              
            # 确保时间以本地时区显示  
            start_time_local = timezone.localtime(booking.start_time) if booking.start_time else ""   
            end_time_local = timezone.localtime(booking.end_time) if booking.end_time else ""   
            created_at_local = timezone.localtime(booking.created_at) if booking.created_at else ""   
  
            # 填充数据  
            worksheet.cell(row=row_num, column=1, value=booking.id).border = thin_border  
            worksheet.cell(row=row_num, column=2, value=booking.creator.display_name or booking.creator.username).border = thin_border  
            worksheet.cell(row=row_num, column=3, value=participants_str).alignment = align_left # 参与者可能多，允许换行  
            worksheet.cell(row=row_num, column=3).border = thin_border  
            worksheet.cell(row=row_num, column=4, value=booking.store.name).border = thin_border  
            worksheet.cell(row=row_num, column=5, value=booking.table.table_number if booking.table else "未分配").border = thin_border  
            worksheet.cell(row=row_num, column=6, value=booking.get_booking_type_display()).border = thin_border  
            worksheet.cell(row=row_num, column=7, value=booking.num_games if booking.num_games is not None else "-").border = thin_border
            worksheet.cell(row=row_num, column=8, value=start_time_local.strftime('%Y-%m-%d %H:%M') if start_time_local else "").border = thin_border
            worksheet.cell(row=row_num, column=9, value=end_time_local.strftime('%Y-%m-%d %H:%M') if end_time_local else "").border = thin_border  
            worksheet.cell(row=row_num, column=10, value=booking.get_status_display()).border = thin_border  
            worksheet.cell(row=row_num, column=11, value=created_at_local.strftime('%Y-%m-%d %H:%M') if created_at_local else "").border = thin_border
              
            row_num += 1  
  
        workbook.save(response) # 将工作簿保存到响应中  
        return response  
  
    export_bookings_to_xlsx.short_description = "导出选中的对局记录为 XLSX"   

    def export_schedule_to_xlsx(self, request, queryset):
        queryset, start_dt, end_dt = self._filter_queryset_by_dates(request, queryset)
        if not start_dt:
            self.message_user(request, "请至少选择一个开始日期以导出课表。", level='ERROR')
            return
        if not end_dt:
            end_dt = start_dt
        if end_dt < start_dt:
            start_dt, end_dt = end_dt, start_dt

        bookings = queryset.select_related('store', 'table', 'creator')
        if not bookings.exists():
            self.message_user(request, "选定范围内没有预约记录。", level='WARNING')
            return

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="mahjong_schedule.xlsx"'

        workbook = Workbook()
        workbook.remove(workbook.active)

        local_tz = timezone.get_current_timezone()
        day_cursor = start_dt.date()
        end_day = end_dt.date()

        while day_cursor <= end_day:
            day_start = datetime.datetime.combine(day_cursor, datetime.time.min, tzinfo=local_tz)
            day_end = datetime.datetime.combine(day_cursor, datetime.time.max, tzinfo=local_tz)

            day_bookings = [
                b for b in bookings
                if timezone.localtime(b.start_time, local_tz) <= day_end and timezone.localtime(b.end_time, local_tz) >= day_start
            ]

            stores = {}
            for b in day_bookings:
                stores.setdefault(b.store_id, {'store': b.store, 'bookings': []})
                stores[b.store_id]['bookings'].append(b)

            for info in stores.values():
                store = info['store']
                store_tables = list(store.tables.all().order_by('table_number'))
                sheet_name = f"{day_cursor.strftime('%m%d')}-{store.name}"[:31]
                sheet = workbook.create_sheet(title=sheet_name)

                header = ["时间"] + [t.table_number for t in store_tables] + ["未分配"]
                sheet.append(header)
                bold_font = Font(bold=True)
                for col in range(1, len(header) + 1):
                    cell = sheet.cell(row=1, column=col)
                    cell.font = bold_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                for hour in range(24):
                    slot_start = day_start + datetime.timedelta(hours=hour)
                    slot_end = slot_start + datetime.timedelta(hours=1)
                    row = [f"{slot_start.strftime('%H:%M')} - {slot_end.strftime('%H:%M')}"]
                    table_texts = [""] * len(store_tables)
                    unassigned_texts = []

                    for booking in info['bookings']:
                        start = timezone.localtime(booking.start_time, local_tz)
                        end = timezone.localtime(booking.end_time, local_tz)
                        if start >= slot_end or end <= slot_start:
                            continue

                        text = f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}\n{booking.creator.display_name or booking.creator.username}\n{booking.get_booking_type_display()}"
                        if booking.table:
                            try:
                                idx = store_tables.index(booking.table)
                                table_texts[idx] = text if not table_texts[idx] else f"{table_texts[idx]}\n{text}"
                            except ValueError:
                                unassigned_texts.append(text)
                        else:
                            unassigned_texts.append(text)

                    row.extend(table_texts)
                    row.append("\n\n".join(unassigned_texts))
                    sheet.append(row)

            day_cursor += datetime.timedelta(days=1)

        workbook.save(response)
        return response

    export_schedule_to_xlsx.short_description = "导出对局记录（按日期范围）"
  
    # --- 核心改动 1: 动态显示和编辑字段 (与修复无关，保持不变) ---   
    def get_fieldsets(self, request, obj=None):   
        fieldsets = []   
        if obj is None:   
            fieldsets.append(('基本信息', {   
                'fields': ('creator', 'store', 'booking_type', 'status', 'start_time', 'end_time', 'num_games', 'table')   
            }))   
            fieldsets.append(('参与者', {'fields': ('participants',)}))   
        else:   
            base_info_fields = ['creator', 'store', 'booking_type', 'status', 'start_time']   
            if obj.booking_type == 'GAMES':   
                base_info_fields.append('num_games')   
            else:   
                base_info_fields.append('end_time')   
            base_info_fields.append('table')   
            fieldsets.append(('基本信息', {'fields': tuple(base_info_fields)}))   
            fieldsets.append(('参与者', {'fields': ('participants',)})) # 参与者总是需要显示
        return fieldsets  
  
    # --- 修复 2: 优化 get_readonly_fields 逻辑 (与修复无关，保持不变) ---   
    def get_readonly_fields(self, request, obj=None):   
        read_only_fields = ['created_at']   
        if obj:   
            read_only_fields.extend(['creator', 'booking_type', 'start_time'])   
            if obj.booking_type == 'GAMES':   
                read_only_fields.append('end_time')   
            else:   
                read_only_fields.append('num_games')   
        return tuple(read_only_fields)   
  
    # --- 核心改动 2: 筛选出可分配的牌桌 (与修复无关，保持不变) ---   
    def formfield_for_foreignkey(self, db_field, request, **kwargs):   
        if db_field.name == "table":   
            obj_id = request.resolver_match.kwargs.get('object_id')   
            if obj_id:   
                booking = self.get_object(request, obj_id)   
                if booking:   
                    conflicting_bookings = Booking.objects.filter(   
                        store=booking.store,   
                        table__isnull=False,   
                        start_time__lt=booking.end_time,   
                        end_time__gt=booking.start_time  
                    ).exclude(pk=booking.pk).exclude(status__in=['CANCELED', 'EXPIRED'])   
                    occupied_table_ids = conflicting_bookings.values_list('table_id', flat=True)   
                    kwargs["queryset"] = MahjongTable.objects.filter(   
                        store=booking.store  
                    ).exclude(id__in=occupied_table_ids)   
            else:   
                kwargs["queryset"] = MahjongTable.objects.all()   
        return super().formfield_for_foreignkey(db_field, request, **kwargs)       
        
@admin.register(CustomUser)   
class CustomUserAdmin(admin.ModelAdmin):   
    list_display = ('username', 'display_name', 'email', 'is_staff', 'is_active')   
    search_fields = ('username', 'display_name', 'email')
