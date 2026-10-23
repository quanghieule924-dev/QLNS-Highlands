from django.db import models
from employees.models import NhanVien  # Import bảng NhanVien từ app employees


# 1. Bảng Chương trình tập sự
class ChuongTrinhTapSu(models.Model):
    ma_ct = models.CharField(primary_key=True, max_length=20, verbose_name="Mã chương trình")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name="Mã nhân viên")
    ten_ct = models.CharField(max_length=255, verbose_name="Tên chương trình")
    trang_thai_duyet = models.CharField(max_length=50, null=True, blank=True, verbose_name="Trạng thái duyệt")
    tong_tien_do = models.FloatField(default=0, verbose_name="Tổng tiến độ (%)")

    def __str__(self):
        return f"{self.ma_ct} - {self.ten_ct}"


# 2. Bảng Bài học
class BaiHoc(models.Model):
    ma_bh = models.CharField(primary_key=True, max_length=20, verbose_name="Mã bài học")
    ma_ct = models.ForeignKey(ChuongTrinhTapSu, on_delete=models.CASCADE, verbose_name="Mã chương trình")
    ten_bh = models.CharField(max_length=255, verbose_name="Tên bài học")
    loai_bh = models.CharField(max_length=50, null=True, blank=True, verbose_name="Loại bài học")
    buoi_hoc = models.IntegerField(null=True, blank=True, verbose_name="Buổi học")
    thoi_gian_hoc = models.IntegerField(null=True, blank=True, verbose_name="Thời gian học (phút)")

    def __str__(self):
        return f"{self.ma_bh} - {self.ten_bh}"


# 3. Bảng Tiến độ tập sự
class TienDoTapSu(models.Model):
    ma_td = models.CharField(primary_key=True, max_length=20, verbose_name="Mã tiến độ")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name="Mã nhân viên")
    ma_bh = models.ForeignKey(BaiHoc, on_delete=models.CASCADE, verbose_name="Mã bài học")
    trang_thai_danh_gia = models.CharField(max_length=50, null=True, blank=True, verbose_name="Trạng thái đánh giá")
    ngay_danh_gia = models.DateField(null=True, blank=True, verbose_name="Ngày đánh giá")

    def __str__(self):
        return f"{self.ma_td} - {self.ma_nv.ho_ten}"


# 4. Bảng Lịch thi
class LichThi(models.Model):
    ma_lt = models.CharField(primary_key=True, max_length=20, verbose_name="Mã lịch thi")
    ma_nv = models.ForeignKey(NhanVien, on_delete=models.CASCADE, verbose_name="Mã nhân viên")
    ngay_thi = models.DateField(verbose_name="Ngày thi")
    ca_thi = models.CharField(max_length=50, verbose_name="Ca thi")

    def __str__(self):
        return f"{self.ma_lt} - {self.ngay_thi}"


# 5. Bảng Đề thi
class DeThi(models.Model):
    ma_dt = models.CharField(primary_key=True, max_length=20, verbose_name="Mã đề thi")
    ma_lt = models.ForeignKey(LichThi, on_delete=models.CASCADE, verbose_name="Mã lịch thi")
    ten_de_thi = models.CharField(max_length=255, verbose_name="Tên đề thi")
    thoi_luong = models.IntegerField(verbose_name="Thời lượng (phút)")

    def __str__(self):
        return f"{self.ma_dt} - {self.ten_de_thi}"


# 6. Bảng Câu hỏi
class CauHoi(models.Model):
    ma_ch = models.CharField(primary_key=True, max_length=20, verbose_name="Mã câu hỏi")
    ma_dt = models.ForeignKey(DeThi, on_delete=models.CASCADE, verbose_name="Mã đề thi")
    noi_dung_ch = models.TextField(verbose_name="Nội dung câu hỏi")
    dap_an_dung = models.CharField(max_length=255, verbose_name="Đáp án đúng")
    diem = models.FloatField(default=0, verbose_name="Điểm câu hỏi")

    def __str__(self):
        return f"{self.ma_ch} - {self.noi_dung_ch[:30]}"


# 7. Bảng Kết quả thi
class KetQuaThi(models.Model):
    ma_kq = models.CharField(primary_key=True, max_length=20, verbose_name="Mã kết quả")
    ma_lt = models.ForeignKey(LichThi, on_delete=models.CASCADE, verbose_name="Mã lịch thi")
    ma_ch = models.ForeignKey(CauHoi, on_delete=models.CASCADE, verbose_name="Mã câu hỏi")
    lan_thi = models.IntegerField(default=1, verbose_name="Lần thi")
    diem_so = models.FloatField(default=0, verbose_name="Điểm số")
    dap_an_da_chon = models.CharField(max_length=255, null=True, blank=True, verbose_name="Đáp án đã chọn")
    thoi_gian_nop_bai = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian nộp bài")
    ket_qua = models.CharField(max_length=50, null=True, blank=True, verbose_name="Kết quả (Đạt/Không đạt)")

    def __str__(self):
        return f"{self.ma_kq} - {self.diem_so}"