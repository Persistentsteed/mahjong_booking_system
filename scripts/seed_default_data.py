"""
向数据库写入默认门店与牌桌信息。
运行方式：python manage.py shell < scripts/seed_default_data.py
"""
from booking.models import Store, MahjongTable

SEED_STORES = [
    ("大钟寺", "北京市海淀区大钟寺", 4),
    ("五道口", "北京市海淀区五道口购物中心", 8),
    ("三里屯", "北京市朝阳区三里屯", 5),
    ("国贸", "北京市朝阳区国贸CBD", 8),
]

created_any = False
for name, address, table_count in SEED_STORES:
    store, created = Store.objects.get_or_create(name=name, defaults={"address": address})
    created_any = created_any or created
    for idx in range(1, table_count + 1):
        MahjongTable.objects.get_or_create(store=store, table_number=f"{name} - {idx}")

if created_any:
    print("已写入默认门店和牌桌。")
else:
    print("门店数据已存在，跳过初始化。")
