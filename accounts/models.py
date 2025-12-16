# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # 覆写 username 字段，使其支持更长的字符和 unicode
    # 这里设置为 150，max_length 可以根据需求调整
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text='必填。150字符以内。仅支持中文、英文字母、数字和 @/./+/-/_',
        validators=[AbstractUser.username_validator], # 仍然使用其自带的校验器
        error_messages={
            'unique': "该用户名已存在。",
        },
        verbose_name='用户名'
    )
    # 昵称或真实姓名，这个字段可以用来显示中文
    display_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="显示名称")
    # 可以添加其他字段，例如头像、电话等

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        # 优先显示 display_name，否则显示 username
        return self.display_name or self.username