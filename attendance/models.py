from django.db import models
from employees.models import NhanVien       # Tham chiếu tới model NhanVien
from scheduling.models import LichLamViec   # Tham chiếu tới model LichLamViec ở app scheduling


class DuLieuKhuonMat(models.Model):
    """Bảng DỮ LIỆU KHUÔN MẶT (DU_LIEU_KHUON_MAT) - Quan hệ 1:1 với NhanVien"""
    ma_nv = models.OneToOneField(
        NhanVien,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='MaNV',
        related_name='du_lieu_khuon_mat',
        verbose_name="Mã nhân viên"
    ) #[cite: 14]
    dl_ma_hoa = models.BinaryField(
        db_column='DLMaHoa',
        verbose_name="Dữ liệu mã hóa khuôn mặt"
    ) #
    ngay_cap_nhat = models.DateTimeField(
        auto_now=True,
        db_column='NgayCapNhat',
        verbose_name="Ngày cập nhật Face ID"
    ) #

    class Meta:
        db_table = 'du_lieu_khuon_mat'
        verbose_name = 'Dữ liệu khuôn mặt'
        verbose_name_plural = 'Dữ liệu khuôn mặt Face ID'


class DuLieuChamCong(models.Model):
    """Bảng DỮ LIỆU CHẤM CÔNG (DU_LIEU_CHAM_CONG)"""
    ma_cham_cong = models.AutoField(
        primary_key=True,
        db_column='MaChamCong',
        verbose_name="Mã chấm công"
    ) #
    ma_lich_lam = models.ForeignKey(
        LichLamViec,
        on_delete=models.CASCADE,
        db_column='MaLichLam',
        related_name='cham_cong_set',
        verbose_name="Lịch làm việc"
    ) #[cite: 14]
    time_checkin = models.DateTimeField(
        null=True,
        blank=True,
        db_column='TimeCheckin',
        verbose_name="Thời gian Check-in"
    ) #
    time_checkout = models.DateTimeField(
        null=True,
        blank=True,
        db_column='TimeCheckout',
        verbose_name="Thời gian Check-out"
    ) #

    class Meta:
        db_table = 'du_lieu_cham_cong'
        verbose_name = 'Dữ liệu chấm công'
        verbose_name_plural = 'Danh sách Dữ liệu chấm công'