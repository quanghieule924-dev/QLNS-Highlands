"""Payroll snapshot models. Do not treat recorded payment as a banking transfer."""
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class CauHinhLuong(models.Model):
    nhan_vien = models.OneToOneField('employees.NhanVien', on_delete=models.PROTECT, related_name='cau_hinh_luong')
    gio_chuan_thang = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))], help_text='Bắt buộc nếu hợp đồng trả theo tháng; dùng để quy đổi lương giờ.')
    he_so_ot = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('1.00'))], help_text='Thiết lập theo chính sách thực tế; không tự suy đoán hệ số OT.')
    khau_tru = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    def __str__(self):
        return f'Cấu hình lương {self.nhan_vien_id}'


class KyLuong(models.Model):
    thang = models.DateField(unique=True, help_text='Ngày đầu tiên của tháng lương')
    da_chot = models.BooleanField(default=False)
    ngay_chot = models.DateTimeField(null=True, blank=True)
    nguoi_chot = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.thang.strftime('%m/%Y')


class PhieuLuong(models.Model):
    PHAN_HOI = [('none', 'Chưa phản hồi'), ('received', 'Đã nhận đủ'), ('issue', 'Báo chưa nhận')]
    ky_luong = models.ForeignKey(KyLuong, on_delete=models.PROTECT, related_name='phieu_luong')
    nhan_vien = models.ForeignKey('employees.NhanVien', on_delete=models.PROTECT, related_name='phieu_luong')
    gio_chuan = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    gio_ot = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    don_gia_gio = models.DecimalField(max_digits=12, decimal_places=2)
    he_so_ot = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    luong_chinh = models.DecimalField(max_digits=14, decimal_places=2)
    luong_ot = models.DecimalField(max_digits=14, decimal_places=2)
    phu_cap = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    khau_tru = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    thuc_nhan = models.DecimalField(max_digits=14, decimal_places=2)
    da_phat_hanh = models.BooleanField(default=False)
    ngay_phat_hanh = models.DateTimeField(null=True, blank=True)
    da_chi_tra = models.BooleanField(default=False)
    ngay_chi_tra = models.DateField(null=True, blank=True)
    phuong_thuc = models.CharField(max_length=30, blank=True)
    ma_tham_chieu = models.CharField(max_length=100, blank=True)
    phan_hoi = models.CharField(max_length=12, choices=PHAN_HOI, default='none')
    ngay_phan_hoi = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['ky_luong', 'nhan_vien'], name='uq_phieu_luong_ky_nhan_vien')]

    def __str__(self):
        return f'{self.nhan_vien_id} - {self.ky_luong}'
