from django.db import models
from employees.models import NhanVien


class HopDong(models.Model):
    mahd = models.CharField(
        max_length=20, primary_key=True, db_column="MaHD"
    )
    nhan_vien = models.ForeignKey(
        NhanVien,
        on_delete=models.PROTECT,
        db_column="MaNV",
        related_name="hop_dong"
    )
    hop_dong_truoc = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="MaHD_truoc",
        related_name="hop_dong_ke_tiep"
    )
    so_hd = models.CharField(max_length=50, db_column="SoHD")
    loai_hd = models.CharField(max_length=100, db_column="LoaiHD")
    ngay_bat_dau = models.DateField(db_column="Ngay_bat_dau")
    ngay_ket_thuc = models.DateField(
        null=True, blank=True, db_column="Ngay_ket_thuc"
    )
    luong_co_ban = models.DecimalField(
        max_digits=12, decimal_places=2, db_column="Luong_co_ban"
    )
    don_gia_gio = models.DecimalField(
        max_digits=12, decimal_places=2, db_column="Don_gia_gio"
    )
    trang_thai_hd = models.CharField(
        max_length=50, db_column="Trang_thai_HD"
    )
    ngay_ky = models.DateField(db_column="Ngay_ky")

    class Meta:
        db_table = "HopDong"

    def __str__(self):
        return self.so_hd


class ThongBao(models.Model):
    matb = models.CharField(max_length=20, primary_key=True, db_column="MaTB")
    hop_dong = models.ForeignKey(
        HopDong, on_delete=models.CASCADE, db_column="MaHD",
        related_name="thong_bao"
    )
    noi_dung = models.TextField(db_column="Noi_dung")
    trang_thai = models.CharField(max_length=50, db_column="Trang_thai")

    class Meta:
        db_table = "ThongBao"

    def __str__(self):
        return self.matb


class YeuCauNghiTruocHan(models.Model):
    mayc = models.CharField(max_length=20, primary_key=True, db_column="MaYC")
    hop_dong = models.ForeignKey(
        HopDong, on_delete=models.CASCADE, db_column="MaHD",
        related_name="yeu_cau_nghi"
    )
    ngay_gui = models.DateField(db_column="Ngay_gui")
    ngay_muon_nghi = models.DateField(db_column="Ngay_muon_nghi")
    ly_do = models.TextField(db_column="Ly_do")
    trang_thai_duyet = models.CharField(
        max_length=50, db_column="Trang_thai_duyet"
    )
    ngay_duyet = models.DateField(
        null=True, blank=True, db_column="Ngay_duyet"
    )

    class Meta:
        db_table = "YeuCauNghiTruocHan"

    def __str__(self):
        return self.mayc


class YeuCauChinhSuaHD(models.Model):
    macs = models.CharField(max_length=20, primary_key=True, db_column="MaCS")
    hop_dong = models.ForeignKey(
        HopDong, on_delete=models.CASCADE, db_column="MaHD",
        related_name="yeu_cau_chinh_sua"
    )
    ngay_yeu_cau = models.DateField(db_column="Ngay_yeu_cau")
    noi_dung = models.TextField(db_column="Noi_dung")
    trang_thai_cs = models.CharField(
        max_length=50, db_column="Trang_thai_CS"
    )

    class Meta:
        db_table = "YeuCauChinhSuaHD"

    def __str__(self):
        return self.macs


class BHXH(models.Model):
    mabh = models.CharField(max_length=20, primary_key=True, db_column="MaBH")
    hop_dong = models.OneToOneField(
        HopDong,
        on_delete=models.CASCADE,
        db_column="MaHD",
        related_name="bhxh",
        null=False
    )
    ma_so_bh = models.CharField(max_length=50, db_column="MaSoBH")
    muc_dong = models.DecimalField(
        max_digits=12, decimal_places=2, db_column="Muc_dong"
    )
    ngay_tham_gia = models.DateField(db_column="Ngaythamgia")
    trang_thai = models.CharField(max_length=50, db_column="Trang_thai")

    class Meta:
        db_table = "BHXH"

    def __str__(self):
        return self.mabh


class CheDoPhucLoi(models.Model):
    mapl = models.CharField(max_length=20, primary_key=True, db_column="MaPL")
    ten_pl = models.CharField(max_length=255, db_column="TenPL")
    mo_ta = models.TextField(
        db_column="Mo_ta",
        blank=True
    )
    dieu_kien_huong = models.TextField(
        db_column="Dieu_kien_huong",
        blank=True
    )

    class Meta:
        db_table = "CheDoPhucLoi"

    def __str__(self):
        return self.ten_pl


class PhucLoiHopDong(models.Model):
    maplhd = models.CharField(
        max_length=20, primary_key=True, db_column="MaPLHD"
    )
    hop_dong = models.ForeignKey(
        HopDong, on_delete=models.CASCADE, db_column="MaHD",
        related_name="phuc_loi_hop_dong"
    )
    che_do = models.ForeignKey(
        CheDoPhucLoi, on_delete=models.PROTECT, db_column="MaPL",
        related_name="hop_dong_ap_dung"
    )
    gia_tri = models.DecimalField(
        max_digits=12, decimal_places=2, db_column="Gia_tri"
    )

    class Meta:
        db_table = "PhucLoiHopDong"

    def __str__(self):
        return self.maplhd


class PhuCap(models.Model):
    mapc = models.CharField(max_length=20, primary_key=True, db_column="MaPC")
    hop_dong = models.ForeignKey(
        HopDong, on_delete=models.CASCADE, db_column="MaHD",
        related_name="phu_cap"
    )
    loai_pc = models.CharField(max_length=100, db_column="LoaiPC")
    gia_tri = models.DecimalField(
        max_digits=12, decimal_places=2, db_column="Gia_tri"
    )
    thang_ap_dung = models.CharField(
        max_length=20, db_column="Thang_ap_dung"
    )

    class Meta:
        db_table = "PhuCap"

    def __str__(self):
        return self.mapc

