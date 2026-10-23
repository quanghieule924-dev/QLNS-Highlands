from django.db import models
from employees.models import NhanVien  # Tham chiếu tới model NhanVien ở app employees


class CaLamViec(models.Model):
    """Bảng CA LÀM VIỆC (CA_LAM_VIEC)"""
    ma_ca_lam = models.CharField(
        max_length=20,
        primary_key=True,
        db_column='MaCaLam',
        verbose_name="Mã ca làm"
    )  # [cite: 15]
    ten_ca = models.CharField(
        max_length=50,
        db_column='TenCaLam',
        verbose_name="Tên ca làm"
    )  # [cite: 15]
    start_time = models.TimeField(
        db_column='StartTime',
        verbose_name="Thời gian bắt đầu ca"
    )  # [cite: 15]
    end_time = models.TimeField(
        db_column='EndTime',
        verbose_name="Thời gian kết thúc ca"
    )  # [cite: 15]

    class Meta:
        db_table = 'ca_lam_viec'
        verbose_name = 'Ca làm việc'
        verbose_name_plural = 'Danh sách Ca làm việc'

    def __str__(self):
        return f"{self.ten_ca} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class DangKyCa(models.Model):
    """Bảng ĐĂNG KÝ CA (DANG_KY_CA)"""
    ma_dk = models.AutoField(
        primary_key=True,
        db_column='MaDK',
        verbose_name="Mã đơn đăng ký"
    )  # [cite: 15]
    ma_nv = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        db_column='MaNV',
        related_name='dang_ky_ca_set',
        verbose_name="Nhân viên đăng ký"
    )  # [cite: 14, 15]
    ma_ca_lam = models.ForeignKey(
        CaLamViec,
        on_delete=models.CASCADE,
        db_column='MaCaLam',
        related_name='dang_ky_ca_set',
        verbose_name="Ca làm đăng ký"
    )  # [cite: 14, 15]
    ngay_lam_dang_ky = models.DateField(
        db_column='NgayLamDangKy',
        verbose_name="Ngày làm đăng ký"
    )  # [cite: 15]
    thoi_diem_dang_ky = models.DateTimeField(
        auto_now_add=True,
        db_column='ThoiDiemDangKy',
        verbose_name="Thời điểm đăng ký"
    )  # [cite: 15]

    class Meta:
        db_table = 'dang_ky_ca'
        verbose_name = 'Đăng ký ca'
        verbose_name_plural = 'Danh sách Đăng ký ca'
        unique_together = ('ma_nv', 'ma_ca_lam', 'ngay_lam_dang_ky')


class LichLamViec(models.Model):
    """Bảng LỊCH LÀM VIỆC (LICH_LAM_VIEC)"""
    ma_lich_lam = models.AutoField(
        primary_key=True,
        db_column='MaLichLam',
        verbose_name="Mã lịch làm"
    )  # [cite: 17]
    ma_nv = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        db_column='MaNV',
        related_name='lich_lam_set',
        verbose_name="Nhân viên"
    )  # [cite: 14, 17]
    ma_ca_lam = models.ForeignKey(
        CaLamViec,
        on_delete=models.CASCADE,
        db_column='MaCaLam',
        related_name='lich_lam_set',
        verbose_name="Ca làm việc"
    )  # [cite: 14, 17]
    ngay_lam = models.DateField(
        db_column='NgayLam',
        verbose_name="Ngày làm việc"
    )  # [cite: 17]

    class Meta:
        db_table = 'lich_lam_viec'
        verbose_name = 'Lịch làm việc'
        verbose_name_plural = 'Bảng Lịch làm việc'

    def __str__(self):
        return f"{self.ma_nv} - {self.ma_ca_lam.ten_ca} ({self.ngay_lam})"


class YeuCauDoiCa(models.Model):
    """Bảng YÊU CẦU ĐỔI CA (YEU_CAU_DOI_CA)"""
    ma_yeu_cau = models.AutoField(
        primary_key=True,
        db_column='MaYeuCau',
        verbose_name="Mã đơn yêu cầu"
    )  # [cite: 16]
    ma_nv_nhan_ca = models.ForeignKey(
        NhanVien,
        on_delete=models.CASCADE,
        db_column='MaNVNhanCa',
        related_name='yeu_cau_doi_ca_nhan_set',
        verbose_name="Nhân viên nhận ca"
    )  # [cite: 14, 16]
    ma_lich_lam_gui = models.ForeignKey(
        LichLamViec,
        on_delete=models.CASCADE,
        db_column='MaLichLamGui',
        related_name='yeu_cau_gui_set',
        verbose_name="Lịch làm gửi đổi"
    )  # [cite: 14, 16]
    ma_lich_lam_nhan = models.ForeignKey(
        LichLamViec,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='MaLichLamNhan',
        related_name='yeu_cau_nhan_set',
        verbose_name="Lịch làm nhận đổi"
    )  # [cite: 14, 16]
    trang_thai = models.CharField(
        max_length=30,
        default='Chờ duyệt',
        db_column='TrangThai',
        verbose_name="Trạng thái"
    )  # [cite: 16]
    ly_do_tu_choi = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column='LyDoTuChoi',
        verbose_name="Lý do từ chối"
    )  # [cite: 16]
    thoi_diem_tao = models.DateTimeField(
        auto_now_add=True,
        db_column='ThoiDiemTao',
        verbose_name="Thời điểm tạo"
    )  # [cite: 16]
    thoi_diem_duyet = models.DateTimeField(
        null=True,
        blank=True,
        db_column='ThoiDiemDuyet',
        verbose_name="Thời điểm duyệt"
    )  # [cite: 16]

    class Meta:
        db_table = 'yeu_cau_doi_ca'
        verbose_name = 'Yêu cầu đổi ca'
        verbose_name_plural = 'Danh sách Yêu cầu đổi ca'



