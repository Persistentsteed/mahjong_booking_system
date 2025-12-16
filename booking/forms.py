# booking/forms.py

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# 我们将继承 Django 内置的用户创建表单
# 这样可以自动获得用户名、密码输入、密码确认和相关的验证逻辑
class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        # 我们基于内置的 User 模型创建表单
        model = User
        # 在表单上显示的字段
        fields = ('username',) # 您也可以添加 'email', 'first_name', 'last_name' 等