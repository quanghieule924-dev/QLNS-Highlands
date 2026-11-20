from django.db import models
from employees.models import NhanVien

class CaLamViec(models.Model):
    ma_ca_lam = models.CharField(max_length=20, primary_key=True, db_column='MaCaLam', verbose_name="Mã ca làm")
    ten_ca = models.CharField(max_length=50, db_column='TenCa', verbose_name="Tên ca làm")
    start_time = models.TimeField(db_column='StartTime', verbose_name="Thời gian bắt đầu")
    end_time = models.TimeField(db_column='EndTime', verbose_name="Thời gian kết thúc")
    class Meta: db_table = 'ca_lam_viec'
    def __str__(self): return self.ten_ca

class DotDangKy(models.Model):
    ten_dot = models.CharField(max_length=100, verbose_name="Tên đợt đăng ký")
    ngay_bat_dau_tuan = models.DateField(verbose_name="Ngày bắt đầu tuần làm việc")
    ngay_ket_thuc_tuan = models.DateField(verbose_name="Ngày kết thúc tuần làm việc")
    han_nhan_dang_ky = models.DateTimeField(verbose_name="Hạn chót nhận form")
    trang_thai = models.CharField(max_length=20, default='Mở form')
    thoi_gian_tao = models.DateTimeField(auto_now_add=True)
    class Meta: db_table = 'dot_dang_ky'
    def __str__(self): return self.ten_dot

class DangKyCa(models.Model):
    ma_dk = models.AutoField(primary_key=True, db_column='MaDK')
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, db_column='MaNV')
    ma_ca_lam = models.ForeignKey(CaLamViec, on_delete=models.CASCADE, db_column='MaCaLam')
    dot_dang_ky = models.ForeignKey(DotDangKy, on_delete=models.CASCADE, null=True, db_column='MaDotDangKy')
    ngay_lam_dang_ky = models.DateField(db_column='NgayLamDangKy')
    thoi_diem_dang_ky = models.DateTimeField(auto_now_add=True, null=True, db_column='ThoiDiemDangKy')
    class Meta:
        db_table = 'dang_ky_ca'
        unique_together = ('ma_nv', 'ma_ca_lam', 'ngay_lam_dang_ky')

class LichLamViec(models.Model):
    ma_lich_lam = models.AutoField(primary_key=True, db_column='MaLichLam')
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, db_column='MaNV')
    ma_ca_lam = models.ForeignKey(CaLamViec, on_delete=models.CASCADE, db_column='MaCaLam')
    dot_dang_ky = models.ForeignKey(DotDangKy, on_delete=models.CASCADE, null=True, db_column='MaDotDangKy')
    ngay_lam = models.DateField(db_column='NgayLam')
    is_published = models.BooleanField(default=False)
    class Meta: db_table = 'lich_lam_viec'

class YeuCauDoiCa(models.Model):
    ma_yeu_cau = models.AutoField(primary_key=True, db_column='MaYeuCau')
    ma_nv_nhan_ca = models.ForeignKey(NhanVien, on_delete=models.CASCADE, related_name='nhan_ca')
    ma_lich_lam_gui = models.ForeignKey(LichLamViec, on_delete=models.CASCADE)
    trang_thai = models.CharField(max_length=30, default='Chờ duyệt')
    class Meta: db_table = 'yeu_cau_doi_ca'

class LuotNopDangKy(models.Model):
    ma_nv = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        related_name='luot_nop_dang_ky'
    )

    dot_dang_ky = models.ForeignKey(
        DotDangKy,
        on_delete=models.CASCADE,
        related_name='luot_nop'
    )

    da_nop = models.BooleanField(default=True)

    lan_nop_dau = models.DateTimeField(auto_now_add=True)

    cap_nhat_cuoi = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'luot_nop_dang_ky'
        constraints = [
            models.UniqueConstraint(
                fields=['ma_nv', 'dot_dang_ky'],
                name='unique_submit_employee_round'
            )
        ]


class DinhBienCa(models.Model):
    dot_dang_ky = models.ForeignKey(
        DotDangKy,
        on_delete=models.CASCADE,
        related_name='dinh_bien'
    )

    ma_ca_lam = models.ForeignKey(
        CaLamViec,
        on_delete=models.CASCADE,
        related_name='dinh_bien'
    )

    vi_tri = models.CharField(max_length=30)

    so_luong = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'dinh_bien_ca'
        constraints = [
            models.UniqueConstraint(
                fields=['dot_dang_ky', 'ma_ca_lam', 'vi_tri'],
                name='unique_staffing_round_shift_role'
            )
        ]