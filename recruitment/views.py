from django.utils import timezone
from employees.models import NhanVien  # Import bảng Nhân viên chung của nhóm
from .models import UngVien


def xac_nhan_nhan_viec(request, ma_ung_vien_dau):
    # 1. Lấy thông tin ứng viên vừa đậu
    ung_vien = UngVien.objects.get(ma_ung_vien=ma_ung_vien_dau)

    # 2. Tạo mã nhân viên mới (Ví dụ: Thêm tiền tố NV vào trước mã ứng viên)
    ma_nhan_vien_moi = f"NV_{ung_vien.ma_ung_vien}"

    # 3. Tạo record Nhân viên mới trên database dùng chung
    NhanVien.objects.create(
        manv=ma_nhan_vien_moi,
        ho_ten=ung_vien.ho_ten,
        ngay_sinh=ung_vien.ngay_sinh,
        sdt=ung_vien.sdt,
        email=ung_vien.email,
        gioi_tinh=ung_vien.gioi_tinh,
        vi_tri=ung_vien.vi_tri,
        dia_chi=ung_vien.dia_chi,
        trang_thai="Thử việc",  # Mặc định là Thử việc khi mới vào
        ngay_vao_lam=timezone.now().date()
    )

    # 4. Cập nhật trạng thái ứng viên để không bị lọc lại
    ung_vien.trang_thai = "Đã thành nhân viên"
    ung_vien.save()

    # ... trả về thông báo thành công cho giao diện ...