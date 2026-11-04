from django.db import models
from django.conf import settings

from django.conf import settings # Huyền thêm

# Create your models here.

class NhanVien(models.Model):
    #Huyền
    tai_khoan = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nhan_vien',
        verbose_name='Tài khoản'
    ) #huyền

    manv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã nhân viên")
    ho_ten = models.CharField(max_length=255, verbose_name="Họ tên")
    ngay_sinh = models.DateField(verbose_name="Ngày sinh", null=True, blank=True)
    sdt = models.CharField(max_length=15, verbose_name="SĐT", null=True, blank=True)
    email = models.EmailField(verbose_name="Email", null=True, blank=True)
    gioi_tinh = models.CharField(max_length=10, verbose_name="Giới tính", null=True, blank=True)
    vi_tri = models.CharField(max_length=255, verbose_name="Vị trí", null=True, blank=True)
    dia_chi = models.TextField(verbose_name="Địa chỉ", null=True, blank=True)
    trang_thai = models.CharField(max_length=50, verbose_name="Trạng thái", null=True, blank=True)
    ngay_vao_lam = models.DateField(verbose_name="Ngày vào làm", null=True, blank=True)
    tai_khoan = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='ho_so_nhan_vien')

    def __str__(self):
        return self.ho_ten

class TiepNhanNhanVien(models.Model):
    TRANG_THAI_CHOICES = [
        ('CHO_TIEP_NHAN', 'Chờ tiếp nhận'),
        ('DA_TAO_HO_SO', 'Đã tạo hồ sơ nhân viên'),
        ('DA_CHUYEN_DAO_TAO', 'Đã chuyển đào tạo'),
    ]

    ho_so = models.OneToOneField(
        'recruitment.HoSoUngTuyen',
        on_delete=models.CASCADE,
        related_name='tiep_nhan_nhan_vien'
    )

    nhan_vien = models.OneToOneField(
        'NhanVien',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ho_so_tiep_nhan'
    )

    trang_thai = models.CharField(
        max_length=30,
        choices=TRANG_THAI_CHOICES,
        default='CHO_TIEP_NHAN'
    )

    chi_nhanh = models.CharField(max_length=255, blank=True, default='')
    ghi_chu = models.TextField(blank=True, default='')

    nguoi_tiep_nhan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    ngay_tiep_nhan = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tiếp nhận nhân viên'
        verbose_name_plural = 'Tiếp nhận nhân viên'
        ordering = ['-created_at']

    def __str__(self):
        return f'Tiếp nhận - {self.ho_so_id}'