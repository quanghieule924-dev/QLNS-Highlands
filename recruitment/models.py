from django.db import models

class ViTriTuyenDung(models.Model):
    ma_vi_tri = models.CharField(max_length=20, primary_key=True, verbose_name="Mã vị trí")
    ten_vi_tri = models.CharField(max_length=100, verbose_name="Tên vị trí")
    mo_ta = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    trang_thai = models.CharField(max_length=50, verbose_name="Trạng thái")

    def __str__(self):
        return self.ten_vi_tri

class DotTuyenDung(models.Model):
    ma_dot = models.CharField(max_length=20, primary_key=True, verbose_name="Mã đợt tuyển dụng")
    ten_dot = models.CharField(max_length=255, verbose_name="Tên đợt tuyển dụng")
    so_luong_can_tuyen = models.IntegerField(verbose_name="Số lượng cần tuyển")
    ngay_bat_dau = models.DateField(verbose_name="Ngày bắt đầu")
    ngay_ket_thuc = models.DateField(verbose_name="Ngày kết thúc")
    ma_vi_tri = models.ForeignKey(ViTriTuyenDung, on_delete=models.CASCADE, verbose_name="Vị trí tuyển dụng")

    def __str__(self):
        return self.ten_dot

class UngVien(models.Model):
    ma_ung_vien = models.CharField(max_length=20, primary_key=True, verbose_name="Mã ứng viên")
    ho_ten = models.CharField(max_length=100, verbose_name="Họ tên")
    ngay_sinh = models.DateField(verbose_name="Ngày sinh")
    sdt = models.CharField(max_length=15, verbose_name="SĐT")
    email = models.EmailField(verbose_name="Email")
    gioi_tinh = models.CharField(max_length=10, verbose_name="Giới tính")
    vi_tri = models.CharField(max_length=100, verbose_name="Vị trí ứng tuyển")
    dia_chi = models.CharField(max_length=255, verbose_name="Địa chỉ")
    trang_thai = models.CharField(max_length=50, default="Chờ xử lý", verbose_name="Trạng thái")

    def __str__(self):
        return self.ho_ten

class HoSoUngTuyen(models.Model):
    ma_ho_so = models.CharField(max_length=20, primary_key=True, verbose_name="Mã hồ sơ")
    ngay_nop = models.DateField(verbose_name="Ngày nộp")
    trang_thai = models.CharField(max_length=50, verbose_name="Trạng thái")
    cv_ung_vien = models.FileField(upload_to='cv_ung_vien/', verbose_name="CV Ứng viên")
    ma_ung_vien = models.ForeignKey(UngVien, on_delete=models.CASCADE, verbose_name="Ứng viên")
    ma_vi_tri = models.ForeignKey(ViTriTuyenDung, on_delete=models.CASCADE, verbose_name="Vị trí")
    ma_dot = models.ForeignKey(DotTuyenDung, on_delete=models.CASCADE, verbose_name="Đợt tuyển dụng")

class DanhGiaCV(models.Model):
    ma_danh_gia_cv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã đánh giá CV")
    ket_qua = models.CharField(max_length=50, verbose_name="Kết quả")
    ngay_danh_gia = models.DateField(verbose_name="Ngày đánh giá")
    ma_ho_so = models.ForeignKey(HoSoUngTuyen, on_delete=models.CASCADE, verbose_name="Hồ sơ")

class LichPhongVan(models.Model):
    ma_lich_pv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã lịch phỏng vấn")
    thoi_gian_pv = models.DateTimeField(verbose_name="Thời gian phỏng vấn")
    hinh_thuc = models.CharField(max_length=50, verbose_name="Hình thức")
    dia_diem = models.CharField(max_length=255, verbose_name="Địa điểm")
    trang_thai = models.CharField(max_length=50, verbose_name="Trạng thái")
    ma_ho_so = models.ForeignKey(HoSoUngTuyen, on_delete=models.CASCADE, verbose_name="Hồ sơ")

class DanhGiaPhongVan(models.Model):
    ma_danh_gia_pv = models.CharField(max_length=20, primary_key=True, verbose_name="Mã đánh giá PV")
    ket_qua = models.CharField(max_length=50, verbose_name="Kết quả")
    ngay_danh_gia = models.DateField(verbose_name="Ngày đánh giá")
    ma_lich_pv = models.ForeignKey(LichPhongVan, on_delete=models.CASCADE, verbose_name="Lịch phỏng vấn")
    ma_ho_so = models.ForeignKey(HoSoUngTuyen, on_delete=models.CASCADE, verbose_name="Hồ sơ")