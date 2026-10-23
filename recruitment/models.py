from django.db import models
from django.utils import timezone

class Campaign(models.Model):
    name = models.CharField(max_length=255, verbose_name="Tên đợt tuyển dụng")
    is_open = models.BooleanField(default=True, verbose_name="Đang mở")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class JobPosition(models.Model):
    title = models.CharField(max_length=255, verbose_name="Vị trí tuyển dụng")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    is_hiring = models.BooleanField(default=True, verbose_name="Đang tuyển")

    def __str__(self):
        return self.title

class Applicant(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Chờ xét duyệt'),
        ('interviewing', 'Đang phỏng vấn'),
        ('accepted', 'Đã nhận'),
        ('rejected', 'Từ chối'),
    )
    full_name = models.CharField(max_length=255, verbose_name="Họ và tên")
    position = models.ForeignKey(JobPosition, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

class Interview(models.Model):
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField(verbose_name="Lịch phỏng vấn")

    def __str__(self):
        return f"Phỏng vấn {self.applicant.full_name}"