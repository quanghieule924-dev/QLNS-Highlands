
from django.db import models
from django.conf import settings

from employees.models import NhanVien
from scheduling.models import LichLamViec


# ============================================================
# 1. TRẠM CHẤM CÔNG
# ============================================================

class TramChamCong(models.Model):

    ma_tram = models.AutoField(
        primary_key=True,
        verbose_name="Mã trạm"
    )

    ten_tram = models.CharField(
        max_length=100,
        verbose_name="Tên trạm chấm công"
    )

    chi_nhanh = models.CharField(
        max_length=200,
        verbose_name="Chi nhánh"
    )

    ip_cho_phep = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP cho phép"
    )

    dang_hoat_dong = models.BooleanField(
        default=True,
        verbose_name="Đang hoạt động"
    )

    ngay_tao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )
    tai_khoan = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tram_cham_cong',
        verbose_name="Tài khoản đăng nhập trạm"
    )
    class Meta:
        db_table = 'tram_cham_cong'
        verbose_name = 'Trạm chấm công'
        verbose_name_plural = 'Danh sách trạm chấm công'

    def __str__(self):
        return f"{self.ten_tram} - {self.chi_nhanh}"


# ============================================================
# 2. DỮ LIỆU KHUÔN MẶT
# ============================================================

class DuLieuKhuonMat(models.Model):

    ma_nv = models.OneToOneField(
        NhanVien,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='MaNV',
        related_name='du_lieu_khuon_mat',
        verbose_name="Mã nhân viên"
    )

    dl_ma_hoa = models.BinaryField(
        db_column='DLMaHoa',
        verbose_name="Dữ liệu mã hóa khuôn mặt"
    )

    ngay_cap_nhat = models.DateTimeField(
        auto_now=True,
        db_column='NgayCapNhat',
        verbose_name="Ngày cập nhật Face ID"
    )

    # BỔ SUNG: Có cho phép sử dụng Face ID hay không
    dang_hoat_dong = models.BooleanField(
        default=True,
        verbose_name="Face ID đang hoạt động"
    )

    # BỔ SUNG: Ghi nhận thời điểm đồng ý đăng ký
    ngay_dong_y = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ngày đồng ý đăng ký Face ID"
    )

    # BỔ SUNG: Phiên bản mô hình tạo embedding
    phien_ban_mo_hinh = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Mô hình nhận diện"
    )

    class Meta:
        db_table = 'du_lieu_khuon_mat'
        verbose_name = 'Dữ liệu khuôn mặt'
        verbose_name_plural = 'Dữ liệu khuôn mặt Face ID'

    def __str__(self):
        return f"FaceID - {self.ma_nv}"


# ============================================================
# 3. DỮ LIỆU CHẤM CÔNG
# ============================================================

class DuLieuChamCong(models.Model):

    ma_cham_cong = models.AutoField(
        primary_key=True,
        db_column='MaChamCong',
        verbose_name="Mã chấm công"
    )

    ma_lich_lam = models.ForeignKey(
        LichLamViec,
        on_delete=models.CASCADE,
        db_column='MaLichLam',
        related_name='cham_cong_set',
        verbose_name="Lịch làm việc"
    )

    time_checkin = models.DateTimeField(
        null=True,
        blank=True,
        db_column='TimeCheckin',
        verbose_name="Thời gian Check-in"
    )

    ip_checkin = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column='IPCheckin',
        verbose_name="IP Check-in"
    )

    time_checkout = models.DateTimeField(
        null=True,
        blank=True,
        db_column='TimeCheckout',
        verbose_name="Thời gian Check-out"
    )

    ip_checkout = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_column='IPCheckout',
        verbose_name="IP Check-out"
    )

    # GIỮ TRƯỜNG CŨ, chỉ đổi trạng thái mặc định
    trang_thai_cham_cong = models.CharField(
        max_length=30,
        default='Chưa xác minh',
        db_column='TrangThaiChamCong',
        verbose_name="Trạng thái chấm công"
    )

    # BỔ SUNG: Trạm sử dụng lúc Check-in
    tram_checkin = models.ForeignKey(
        TramChamCong,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='luot_checkin',
        verbose_name="Trạm Check-in"
    )

    # BỔ SUNG: Trạm sử dụng lúc Check-out
    tram_checkout = models.ForeignKey(
        TramChamCong,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='luot_checkout',
        verbose_name="Trạm Check-out"
    )

    # BỔ SUNG: Nguồn ghi nhận công
    nguon_cham_cong = models.CharField(
        max_length=30,
        default='Chưa xác định',
        verbose_name="Nguồn chấm công"
    )

    class Meta:
        db_table = 'du_lieu_cham_cong'
        verbose_name = 'Dữ liệu chấm công'
        verbose_name_plural = 'Danh sách Dữ liệu chấm công'

        constraints = [
            models.UniqueConstraint(
                fields=['ma_lich_lam'],
                name='unique_cham_cong_moi_lich'
            )
        ]

    def __str__(self):
        return (
            f"Chấm công #{self.ma_cham_cong} "
            f"- {self.ma_lich_lam.ma_nv}"
        )


# ============================================================
# 4. YÊU CẦU ĐIỀU CHỈNH CHẤM CÔNG
# ============================================================

class YeuCauDieuChinhCong(models.Model):

    TRANG_THAI_CHOICES = [
        ('Cho_duyet', 'Chờ duyệt'),
        ('Da_duyet', 'Đã duyệt'),
        ('Tu_choi', 'Từ chối'),
    ]

    ma_yeu_cau = models.AutoField(
        primary_key=True,
        verbose_name="Mã yêu cầu"
    )

    ma_lich_lam = models.ForeignKey(
        LichLamViec,
        on_delete=models.PROTECT,
        related_name='yeu_cau_dieu_chinh',
        verbose_name="Ca làm việc cần điều chỉnh"
    )

    ly_do = models.TextField(
        verbose_name="Lý do giải trình"
    )

    checkin_de_nghi = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Giờ Check-in đề nghị"
    )

    checkout_de_nghi = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Giờ Check-out đề nghị"
    )

    trang_thai = models.CharField(
        max_length=20,
        choices=TRANG_THAI_CHOICES,
        default='Cho_duyet',
        verbose_name="Trạng thái xử lý"
    )

    ngay_gui = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày gửi yêu cầu"
    )

    nguoi_duyet = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='yeu_cau_cong_da_duyet',
        verbose_name="Người duyệt"
    )

    ngay_duyet = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ngày duyệt"
    )

    ghi_chu_quan_ly = models.TextField(
        blank=True,
        default='',
        verbose_name="Ghi chú quản lý"
    )

    class Meta:
        db_table = 'yeu_cau_dieu_chinh_cong'
        verbose_name = 'Yêu cầu điều chỉnh công'
        verbose_name_plural = 'Danh sách yêu cầu điều chỉnh công'
        ordering = ['-ngay_gui']

    def __str__(self):
        return (
            f"Yêu cầu #{self.ma_yeu_cau} "
            f"- {self.ma_lich_lam.ma_nv}"
        )