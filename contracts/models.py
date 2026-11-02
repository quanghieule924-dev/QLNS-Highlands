
from datetime import datetime, timedelta

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone

from employees.models import NhanVien


# =========================================================
# 1. QUẢN LÝ HỢP ĐỒNG
# =========================================================

class HopDong(models.Model):

    LOAI_HD_CHOICES = [
        ('co_thoi_han', 'Có thời hạn'),
        ('khong_thoi_han', 'Không xác định thời hạn'),
    ]

    HINH_THUC_LUONG_CHOICES = [
        ('theo_gio', 'Theo giờ'),
        ('theo_thang', 'Theo tháng'),
    ]

    TRANG_THAI_CHOICES = [
        ('cho_ky', 'Chờ ký'),
        ('da_ky_cho_hieu_luc', 'Đã ký - Chờ hiệu lực'),
        ('dang_hieu_luc', 'Đang hiệu lực'),
        ('da_het_han', 'Đã hết hạn'),
        ('da_cham_dut', 'Đã chấm dứt'),
    ]

    mahd = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaHD"
    )

    so_hd = models.CharField(
        max_length=50,
        unique=True,
        db_column="SoHD",
        verbose_name="Số hợp đồng"
    )

    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.PROTECT,
        db_column="MaNV",
        related_name="hop_dong"
    )

    # Liên kết với hợp đồng trước khi gia hạn
    hop_dong_truoc = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="MaHD_truoc",
        related_name="hop_dong_ke_tiep"
    )

    loai_hd = models.CharField(
        max_length=30,
        choices=LOAI_HD_CHOICES,
        db_column="LoaiHD",
        verbose_name="Loại hợp đồng"
    )

    ngay_bat_dau = models.DateField(
        db_column="Ngay_bat_dau",
        verbose_name="Ngày bắt đầu"
    )

    ngay_ket_thuc = models.DateField(
        null=True,
        blank=True,
        db_column="Ngay_ket_thuc",
        verbose_name="Ngày kết thúc"
    )

    ngay_ky = models.DateField(
        null=True,
        blank=True,
        db_column="Ngay_ky",
        verbose_name="Ngày ký"
    )

    hinh_thuc_luong = models.CharField(
        max_length=20,
        choices=HINH_THUC_LUONG_CHOICES,
        default='theo_thang',
        db_column="Hinh_thuc_luong",
        verbose_name="Hình thức trả lương"
    )

    muc_luong = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        db_column="Muc_luong",
        verbose_name="Mức lương"
    )

    trang_thai_hd = models.CharField(
        max_length=30,
        choices=TRANG_THAI_CHOICES,
        default='cho_ky',
        db_column="Trang_thai_HD",
        verbose_name="Trạng thái hợp đồng"
    )

    ngay_cham_dut = models.DateField(
        null=True,
        blank=True,
        db_column="Ngay_cham_dut",
        verbose_name="Ngày chấm dứt"
    )

    ly_do_cham_dut = models.TextField(
        blank=True,
        db_column="Ly_do_cham_dut",
        verbose_name="Lý do chấm dứt"
    )

    class Meta:
        db_table = "HopDong"
        ordering = ['-ngay_bat_dau']
        verbose_name = "Hợp đồng"
        verbose_name_plural = "Hợp đồng"



    def clean(self):
        super().clean()

        errors = {}

        # Hợp đồng có thời hạn phải có ngày kết thúc
        if self.loai_hd == 'co_thoi_han' and not self.ngay_ket_thuc:
            errors['ngay_ket_thuc'] = (
                'Hợp đồng có thời hạn phải có ngày kết thúc.'
            )

        # Hợp đồng không xác định thời hạn không có ngày kết thúc
        if self.loai_hd == 'khong_thoi_han' and self.ngay_ket_thuc:
            errors['ngay_ket_thuc'] = (
                'Hợp đồng không xác định thời hạn không cần ngày kết thúc.'
            )

        # Ngày kết thúc phải sau ngày bắt đầu
        if (
            self.ngay_bat_dau
            and self.ngay_ket_thuc
            and self.ngay_ket_thuc <= self.ngay_bat_dau
        ):
            errors['ngay_ket_thuc'] = (
                'Ngày kết thúc phải sau ngày bắt đầu.'
            )

        # Ngày ký không được sau ngày bắt đầu
        if (
            self.ngay_ky
            and self.ngay_bat_dau
            and self.ngay_ky > self.ngay_bat_dau
        ):
            errors['ngay_ky'] = (
                'Ngày ký không được sau ngày bắt đầu hợp đồng.'
            )

        # Hợp đồng trước phải thuộc cùng nhân viên
        if self.hop_dong_truoc and self.nhan_vien:
            if self.hop_dong_truoc.nhan_vien != self.nhan_vien:
                errors['hop_dong_truoc'] = (
                    'Hợp đồng trước phải thuộc cùng một nhân viên.'
                )

        # Không cho phép hợp đồng tự liên kết với chính nó
        if (
                self.pk
                and self.hop_dong_truoc
                and self.hop_dong_truoc.pk == self.pk
        ):
            errors['hop_dong_truoc'] = (
                'Hợp đồng không thể liên kết với chính nó.'
            )

        if errors:
            raise ValidationError(errors)

    @property
    def sap_het_han(self):
        """
        Kiểm tra hợp đồng có thời hạn còn tối đa 30 ngày hay không.
        Không lưu trạng thái này vào database.
        """

        if (
            self.trang_thai_hd != 'dang_hieu_luc'
            or self.loai_hd != 'co_thoi_han'
            or not self.ngay_ket_thuc
        ):
            return False

        hom_nay = timezone.localdate()
        ngay_canh_bao = hom_nay + timedelta(days=30)

        return hom_nay <= self.ngay_ket_thuc <= ngay_canh_bao

    def __str__(self):
        return self.so_hd


# =========================================================
# 2. THÔNG BÁO HỢP ĐỒNG
# =========================================================

class ThongBao(models.Model):

    TRANG_THAI_CHOICES = [
        ('chua_doc', 'Chưa đọc'),
        ('da_doc', 'Đã đọc'),
    ]

    matb = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaTB"
    )

    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="thong_bao"
    )

    noi_dung = models.TextField(
        db_column="Noi_dung"
    )

    trang_thai = models.CharField(
        max_length=50,
        choices=TRANG_THAI_CHOICES,
        default='chua_doc',
        db_column="Trang_thai"
    )

    class Meta:
        db_table = "ThongBao"

    def __str__(self):
        return self.matb


# =========================================================
# 3. YÊU CẦU NGHỈ TRƯỚC HẠN
# =========================================================

class YeuCauNghiTruocHan(models.Model):

    TRANG_THAI_CHOICES = [
        ('cho_duyet', 'Chờ duyệt'),
        ('da_duyet', 'Đã duyệt'),
        ('tu_choi', 'Từ chối'),
        ('da_huy', 'Đã hủy'),
    ]

    mayc = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaYC"
    )

    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="yeu_cau_nghi"
    )

    ngay_gui = models.DateField(
        db_column="Ngay_gui"
    )

    ngay_muon_nghi = models.DateField(
        db_column="Ngay_muon_nghi"
    )

    ly_do = models.TextField(
        db_column="Ly_do"
    )

    trang_thai_duyet = models.CharField(
        max_length=50,
        choices=TRANG_THAI_CHOICES,
        default='cho_duyet',
        db_column="Trang_thai_duyet"
    )

    ngay_duyet = models.DateField(
        null=True,
        blank=True,
        db_column="Ngay_duyet"
    )

    class Meta:
        db_table = "YeuCauNghiTruocHan"
        ordering = ['-ngay_gui']

    def clean(self):
        super().clean()

        if (
            self.ngay_gui
            and self.ngay_muon_nghi
            and self.ngay_muon_nghi <= self.ngay_gui
        ):
            raise ValidationError({
                'ngay_muon_nghi': (
                    'Ngày muốn nghỉ phải sau ngày gửi yêu cầu.'
                )
            })

        if self.trang_thai_duyet == 'da_duyet' and not self.ngay_duyet:
            raise ValidationError({
                'ngay_duyet': 'Cần có ngày duyệt khi yêu cầu đã được duyệt.'
            })

    def __str__(self):
        return self.mayc


# =========================================================
# 4. YÊU CẦU CHỈNH SỬA HỢP ĐỒNG
# =========================================================

class YeuCauChinhSuaHD(models.Model):

    TRANG_THAI_CHOICES = [
        ('cho_duyet', 'Chờ duyệt'),
        ('da_duyet', 'Đã duyệt'),
        ('tu_choi', 'Từ chối'),
        ('da_huy', 'Đã hủy'),
    ]

    macs = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaCS"
    )

    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="yeu_cau_chinh_sua"
    )

    ngay_yeu_cau = models.DateField(
        db_column="Ngay_yeu_cau"
    )

    noi_dung = models.TextField(
        db_column="Noi_dung"
    )

    trang_thai_cs = models.CharField(
        max_length=50,
        choices=TRANG_THAI_CHOICES,
        default='cho_duyet',
        db_column="Trang_thai_CS"
    )

    related_name = "yeu_cau_chinh_sua"


    class Meta:
        db_table = "YeuCauChinhSuaHD"
        ordering = ['-ngay_yeu_cau']

    def __str__(self):
        return self.macs


# =========================================================
# 5. QUẢN LÝ BẢO HIỂM XÃ HỘI
# =========================================================

class BHXH(models.Model):

    TRANG_THAI_CHOICES = [
        ('dang_tham_gia', 'Đang tham gia'),
        ('tam_dung', 'Tạm dừng'),
        ('da_ngung', 'Đã ngừng'),
    ]

    mabh = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaBH"
    )

    hop_dong = models.OneToOneField(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="bhxh"
    )

    ma_so_bh = models.CharField(
        max_length=50,
        db_column="MaSoBH"
    )

    muc_dong = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        db_column="Muc_dong"
    )

    ngay_tham_gia = models.DateField(
        db_column="Ngaythamgia"
    )

    trang_thai = models.CharField(
        max_length=50,
        choices=TRANG_THAI_CHOICES,
        default='dang_tham_gia',
        db_column="Trang_thai"
    )

    class Meta:
        db_table = "BHXH"

    def __str__(self):
        return self.mabh


# =========================================================
# 6. DANH MỤC CHẾ ĐỘ PHÚC LỢI
# =========================================================

class CheDoPhucLoi(models.Model):

    mapl = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaPL"
    )

    ten_pl = models.CharField(
        max_length=255,
        db_column="TenPL"
    )

    mo_ta = models.TextField(
        blank=True,
        db_column="Mo_ta"
    )

    dieu_kien_huong = models.TextField(
        blank=True,
        db_column="Dieu_kien_huong"
    )

    class Meta:
        db_table = "CheDoPhucLoi"
        ordering = ['ten_pl']

    def __str__(self):
        return self.ten_pl


# =========================================================
# 7. PHÚC LỢI ÁP DỤNG CHO HỢP ĐỒNG
# =========================================================

class PhucLoiHopDong(models.Model):

    maplhd = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaPLHD"
    )

    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="phuc_loi_hop_dong"
    )

    che_do = models.ForeignKey(
        CheDoPhucLoi,
        on_delete=models.PROTECT,
        db_column="MaPL",
        related_name="hop_dong_ap_dung"
    )

    gia_tri = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        db_column="Gia_tri"
    )

    class Meta:
        db_table = "PhucLoiHopDong"
        constraints = [
            models.UniqueConstraint(
                fields=['hop_dong', 'che_do'],
                name='unique_phuc_loi_tren_hop_dong'
            )
        ]

    def __str__(self):
        return self.maplhd


# =========================================================
# 8. QUẢN LÝ PHỤ CẤP
# =========================================================

class PhuCap(models.Model):

    mapc = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="MaPC"
    )

    hop_dong = models.ForeignKey(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="phu_cap"
    )

    loai_pc = models.CharField(
        max_length=100,
        db_column="LoaiPC"
    )

    gia_tri = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        db_column="Gia_tri"
    )

    # Quy ước lưu tháng theo định dạng YYYY-MM
    thang_ap_dung = models.CharField(
        max_length=7,
        db_column="Thang_ap_dung",
        help_text="Nhập theo định dạng YYYY-MM, ví dụ 2026-11."
    )

    class Meta:
        db_table = "PhuCap"
        ordering = ['-thang_ap_dung']

    def clean(self):
        super().clean()

        if self.thang_ap_dung:
            try:
                datetime.strptime(
                    self.thang_ap_dung, '%Y-%m'
                )
            except ValueError:
                raise ValidationError({
                    'thang_ap_dung': (
                        'Tháng áp dụng phải có định dạng YYYY-MM.'
                    )
                })

    def __str__(self):
        return self.mapc
