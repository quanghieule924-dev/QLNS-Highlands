from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from employees.models import NhanVien
from .models import UngVien


def xac_nhan_nhan_viec(request, ma_ung_vien_dau):
    # 1. Lấy thông tin ứng viên an toàn (Nếu không có mã này sẽ báo lỗi 404 thay vì sập web)
    ung_vien = get_object_or_404(UngVien, ma_ung_vien=ma_ung_vien_dau)

    try:
        # transaction.atomic đảm bảo Bước 3 và 4 phải cùng thành công, lỡ lỗi sẽ tự Rollback (hủy)
        with transaction.atomic():

            # 2. Tạo mã nhân viên mới
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
                trang_thai="Thử việc",
                ngay_vao_lam=timezone.now().date()
            )

            # 4. Cập nhật trạng thái ứng viên
            ung_vien.trang_thai = "Đã thành nhân viên"
            ung_vien.save()

        # 5. Gửi thông báo xanh lá cây báo thành công cho giao diện
        messages.success(request, f"Đã tiếp nhận {ung_vien.ho_ten} thành nhân viên chính thức!")

    except Exception as e:
        # Báo lỗi màu đỏ nếu có trục trặc database
        messages.error(request, f"Có lỗi xảy ra: {str(e)}")

    # 6. Chuyển hướng người dùng quay lại trang Danh sách ứng viên (bạn cần thay 'ten_url_danh_sach' bằng url thực tế của bạn)
    return redirect('ten_url_danh_sach_ung_vien')