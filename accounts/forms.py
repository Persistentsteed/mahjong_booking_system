# accounts/forms.py

from django.contrib.auth.forms import UserCreationForm
# 从当前 `accounts` 应用（也就是这个文件所在的 app）下的 `models.py` 导入 CustomUser
from .models import CustomUser 

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # 在注册页面，我们希望用户填写用户名和显示名称
        fields = ('username', 'display_name',)