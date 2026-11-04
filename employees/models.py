from django.db import models

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

    def __str__(self):
        return self.ho_ten