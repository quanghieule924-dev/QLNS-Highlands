
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Quản lý'),
        ('employee', 'Nhân viên'),
        ('candidate', 'Ứng viên'),
        ('kiosk', 'Trạm chấm công'),
    ]


    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='employee',
        verbose_name='Vai trò'
    )

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'Tài khoản'
        verbose_name_plural = 'Tài khoản'

    def __str__(self):
        return self.username
