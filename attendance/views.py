
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone

from employees.models import NhanVien
from scheduling.models import LichLamViec
from .models import DuLieuChamCong

import cv2

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import DuLieuKhuonMat
from .services.face_service import (
    FaceProcessingError,
    MODEL_VERSION,
    create_face_embedding,
    encrypt_embedding,
)

from cryptography.fernet import InvalidToken
from .services.face_service import (
    verify_face,
)


from datetime import datetime, timedelta
from django.db import IntegrityError, transaction
from .models import TramChamCong
import calendar

import calendar
from datetime import date
from django.db.models import Q
from django.http import HttpResponse

# ============================================================
# 1. ĐIỀU HƯỚNG CHẤM CÔNG THEO VAI TRÒ
# ============================================================

@login_required
def attendance_dashboard(request):

    role = request.user.role

    if role == 'admin':
        return redirect('attendance:manager_dashboard')

    if role == 'employee':
        return redirect('attendance:employee_dashboard')

    if role == 'kiosk':
        return redirect('attendance:kiosk')

    return HttpResponseForbidden(
        "Tài khoản không có quyền truy cập chức năng chấm công."
    )



# ============================================================
# TRANG CHẤM CÔNG NHÂN VIÊN
# - Chấm công hôm nay
# - Lịch sử chấm công theo tháng
# ============================================================

@login_required
def employee_attendance_dashboard(request):

    if request.user.role != 'employee':
        return HttpResponseForbidden(
            "Chỉ nhân viên được xem chấm công cá nhân."
        )

    # 1. Xác định nhân viên từ tài khoản đăng nhập
    try:
        nhan_vien = NhanVien.objects.get(
            tai_khoan=request.user
        )
    except NhanVien.DoesNotExist:
        return render(
            request,
            'attendance/employee_dashboard.html',
            {
                'loi': 'Tài khoản chưa liên kết hồ sơ nhân viên.',
                'active_menu': 'attendance',
            }
        )

    hom_nay = timezone.localdate()

    # 2. Xác định tab
    tab = request.GET.get('tab', 'today')

    if tab not in ['today', 'history']:
        tab = 'today'

    # 3. Xác định tháng xem lịch sử
    thang_mac_dinh = hom_nay.strftime('%Y-%m')
    thang_chon = request.GET.get('month', thang_mac_dinh)

    try:
        nam, thang = map(int, thang_chon.split('-'))

        if not (2000 <= nam <= 2100 and 1 <= thang <= 12):
            raise ValueError

    except (ValueError, AttributeError):
        nam = hom_nay.year
        thang = hom_nay.month

    thang_chon = f'{nam:04d}-{thang:02d}'

    ngay_dau_thang = datetime(nam, thang, 1).date()
    ngay_cuoi_thang = datetime(
        nam,
        thang,
        calendar.monthrange(nam, thang)[1]
    ).date()

    # 4. Lấy toàn bộ lịch công bố trong tháng
    # Chỉ lấy lịch của nhân viên đang đăng nhập
    lich_trong_thang = list(
        LichLamViec.objects.filter(
            ma_nv=nhan_vien,
            is_published=True,
            ngay_lam__range=(
                ngay_dau_thang,
                ngay_cuoi_thang
            )
        ).select_related(
            'ma_ca_lam'
        ).order_by(
            '-ngay_lam',
            'ma_ca_lam_id'
        )
    )

    # 5. Lấy dữ liệu chấm công tương ứng
    cham_cong_map = {}

    for cong in DuLieuChamCong.objects.filter(
        ma_lich_lam__in=lich_trong_thang
    ).order_by('ma_cham_cong'):

        if cong.ma_lich_lam_id not in cham_cong_map:
            cham_cong_map[cong.ma_lich_lam_id] = cong

    # 6. Chuẩn bị dữ liệu lịch sử
    lich_su = []
    tong_ca_hoan_thanh = 0
    tong_phut_lam = 0

    for lich in lich_trong_thang:

        ca = lich.ma_ca_lam
        cong = cham_cong_map.get(lich.pk)

        # Dùng lại hàm đọc giờ ca đang phục vụ Kiosk
        # Để tránh sai tên trường giờ bắt đầu/kết thúc
        try:
            bat_dau, ket_thuc = lay_gio_ca(lich)
            gio_bat_dau = timezone.localtime(
                bat_dau
            ).time()
            gio_ket_thuc = timezone.localtime(
                ket_thuc
            ).time()
        except ValueError:
            gio_bat_dau = None
            gio_ket_thuc = None

        time_checkin = (
            cong.time_checkin if cong else None
        )

        time_checkout = (
            cong.time_checkout if cong else None
        )

        trang_thai = 'Chưa chấm công'
        mau_trang_thai = 'chua-cham'

        if time_checkin and time_checkout:

            trang_thai = 'Đã Check-out'
            mau_trang_thai = 'da-checkout'

        elif time_checkin:

            trang_thai = 'Đã Check-in'
            mau_trang_thai = 'da-checkin'

        elif time_checkout:

            trang_thai = 'Cần kiểm tra'
            mau_trang_thai = 'can-kiem-tra'

        elif lich.ngay_lam > hom_nay:

            trang_thai = 'Chưa đến ngày'
            mau_trang_thai = 'chua-den-ngay'

        # Tính giờ thực tế nếu có đủ Check-in/Check-out
        so_gio_lam = '—'

        if time_checkin and time_checkout:

            khoang_thoi_gian = (
                time_checkout - time_checkin
            )

            tong_phut = max(
                0,
                int(khoang_thoi_gian.total_seconds() // 60)
            )

            gio = tong_phut // 60
            phut = tong_phut % 60

            so_gio_lam = f'{gio}h {phut:02d}p'

            tong_phut_lam += tong_phut
            tong_ca_hoan_thanh += 1

        lich_su.append({
            'ma_lich_lam': lich.pk,
            'ngay_lam': lich.ngay_lam,
            'ten_ca': ca.ten_ca,
            'gio_bat_dau': gio_bat_dau,
            'gio_ket_thuc': gio_ket_thuc,
            'time_checkin': time_checkin,
            'time_checkout': time_checkout,
            'trang_thai': trang_thai,
            'mau_trang_thai': mau_trang_thai,
            'so_gio_lam': so_gio_lam,
        })

    # 7. Lấy ca của ngày hôm nay
    # Đọc riêng để vẫn hoạt động khi người dùng xem tháng khác
    lich_hom_nay = list(
        LichLamViec.objects.filter(
            ma_nv=nhan_vien,
            ngay_lam=hom_nay,
            is_published=True
        ).select_related(
            'ma_ca_lam'
        ).order_by(
            'ma_ca_lam_id'
        )
    )

    # Tận dụng dữ liệu lịch sử nếu tháng được chọn là tháng hiện tại
    du_lieu_hom_nay = {
        item['ma_lich_lam']: item
        for item in lich_su
        if item['ngay_lam'] == hom_nay
    }

    danh_sach_ca = []

    for lich in lich_hom_nay:

        item = du_lieu_hom_nay.get(lich.pk)

        # Nếu đang xem tháng khác thì lấy dữ liệu hôm nay riêng
        if item is None:

            cong = DuLieuChamCong.objects.filter(
                ma_lich_lam=lich
            ).order_by('ma_cham_cong').first()

            try:
                bat_dau, ket_thuc = lay_gio_ca(lich)
                gio_bat_dau = timezone.localtime(
                    bat_dau
                ).time()
                gio_ket_thuc = timezone.localtime(
                    ket_thuc
                ).time()
            except ValueError:
                gio_bat_dau = None
                gio_ket_thuc = None

            time_checkin = (
                cong.time_checkin if cong else None
            )

            time_checkout = (
                cong.time_checkout if cong else None
            )

            if time_checkin and time_checkout:
                trang_thai = 'Đã Check-out'
                mau_trang_thai = 'da-checkout'
            elif time_checkin:
                trang_thai = 'Đã Check-in'
                mau_trang_thai = 'da-checkin'
            elif time_checkout:
                trang_thai = 'Cần kiểm tra'
                mau_trang_thai = 'can-kiem-tra'
            else:
                trang_thai = 'Chưa chấm công'
                mau_trang_thai = 'chua-cham'

            item = {
                'ma_lich_lam': lich.pk,
                'ngay_lam': lich.ngay_lam,
                'ten_ca': lich.ma_ca_lam.ten_ca,
                'gio_bat_dau': gio_bat_dau,
                'gio_ket_thuc': gio_ket_thuc,
                'time_checkin': time_checkin,
                'time_checkout': time_checkout,
                'trang_thai': trang_thai,
                'mau_trang_thai': mau_trang_thai,
            }

        danh_sach_ca.append(item)

    context = {
        'nhan_vien': nhan_vien,
        'hom_nay': hom_nay,
        'tab': tab,
        'thang_chon': thang_chon,
        'danh_sach_ca': danh_sach_ca,
        'tong_so_ca': len(danh_sach_ca),
        'lich_su': lich_su,
        'tong_ca_hoan_thanh': tong_ca_hoan_thanh,
        'tong_so_ca_thang': len(lich_su),
        'tong_gio_lam': (
            f'{tong_phut_lam // 60}h '
            f'{tong_phut_lam % 60:02d}p'
        ),
        'active_menu': 'attendance',
    }

    return render(
        request,
        'attendance/employee_dashboard.html',
        context
    )



# ============================================================
# DASHBOARD CHẤM CÔNG - QUẢN LÝ
# TAB 1: CHẤM CÔNG HÔM NAY
# ============================================================

@login_required
def manager_attendance_dashboard(request):

    # 1. Kiểm tra quyền truy cập
    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Chỉ quản lý được xem bảng tổng hợp chấm công."
        )

    # 2. Lấy ngày hiện tại theo múi giờ Việt Nam
    hom_nay = timezone.localdate()
    hien_tai = timezone.now()

    # 3. Lấy các ca làm việc đã công bố hôm nay
    lich_hom_nay = list(
        LichLamViec.objects.filter(
            ngay_lam=hom_nay,
            is_published=True
        ).select_related(
            'ma_nv',
            'ma_ca_lam'
        ).order_by(
            'ma_ca_lam_id',
            'ma_nv_id'
        )
    )

    # 4. Lấy dữ liệu chấm công liên kết với các ca
    du_lieu_cham_cong = DuLieuChamCong.objects.filter(
        ma_lich_lam__in=lich_hom_nay
    ).order_by('ma_cham_cong')

    cham_cong_map = {}

    for cong in du_lieu_cham_cong:
        if cong.ma_lich_lam_id not in cham_cong_map:
            cham_cong_map[cong.ma_lich_lam_id] = cong

    # 5. Khởi tạo số liệu thống kê
    tong_luot_ca = len(lich_hom_nay)
    da_checkin = 0
    chua_checkin = 0
    da_checkout = 0
    di_muon = 0

    danh_sach_cham_cong = []

    # Cho phép đi muộn tối đa 5 phút để minh họa
    nguong_di_muon = 5

    for lich in lich_hom_nay:

        nhan_vien = lich.ma_nv
        ca = lich.ma_ca_lam
        cong = cham_cong_map.get(lich.pk)

        time_checkin = cong.time_checkin if cong else None
        time_checkout = cong.time_checkout if cong else None

        # 6. Lấy giờ bắt đầu và kết thúc của ca
        try:
            bat_dau, ket_thuc = lay_gio_ca(lich)
        except ValueError:
            bat_dau = None
            ket_thuc = None

        # 7. Xác định trạng thái
        trang_thai = 'Chưa Check-in'
        mau_trang_thai = 'chua-checkin'

        if time_checkin:
            da_checkin += 1

            if time_checkout:
                da_checkout += 1
                trang_thai = 'Đã Check-out'
                mau_trang_thai = 'da-checkout'
            else:
                trang_thai = 'Đã Check-in'
                mau_trang_thai = 'da-checkin'

        else:
            chua_checkin += 1

            if bat_dau and hien_tai < bat_dau:
                trang_thai = 'Chưa đến giờ'
                mau_trang_thai = 'chua-den-gio'

        # 8. Kiểm tra đi muộn
        so_phut_muon = 0
        ghi_chu = '—'

        if time_checkin and bat_dau:

            do_tre = (
                time_checkin - bat_dau
            ).total_seconds() / 60

            if do_tre > nguong_di_muon:
                so_phut_muon = max(0, int(do_tre))
                di_muon += 1
                ghi_chu = f'Đi muộn {so_phut_muon} phút'

        # 9. Tính thời gian làm thực tế
        so_gio_lam = '—'

        if time_checkin and time_checkout:

            tong_phut = max(
                0,
                int(
                    (time_checkout - time_checkin)
                    .total_seconds() // 60
                )
            )

            so_gio_lam = (
                f'{tong_phut // 60}h '
                f'{tong_phut % 60:02d}p'
            )

        # 10. Đưa vào danh sách hiển thị
        danh_sach_cham_cong.append({
            'ma_lich_lam': lich.pk,
            'ma_nv': nhan_vien.pk,
            'ho_ten': nhan_vien.ho_ten,
            'ten_ca': ca.ten_ca,
            'gio_bat_dau': bat_dau,
            'gio_ket_thuc': ket_thuc,
            'time_checkin': time_checkin,
            'time_checkout': time_checkout,
            'trang_thai': trang_thai,
            'mau_trang_thai': mau_trang_thai,
            'so_gio_lam': so_gio_lam,
            'ghi_chu': ghi_chu,
        })

    # 11. Truyền dữ liệu xuống HTML
    context = {
        'active_menu': 'attendance',
        'hom_nay': hom_nay,
        'tong_luot_ca': tong_luot_ca,
        'da_checkin': da_checkin,
        'chua_checkin': chua_checkin,
        'da_checkout': da_checkout,
        'di_muon': di_muon,
        'danh_sach_cham_cong': danh_sach_cham_cong,
    }

    return render(
        request,
        'attendance/manager_dashboard.html',
        context
    )



# ============================================================
# 4. TRẠM CHẤM CÔNG FACE ID - TÀI KHOẢN KIOSK
# ============================================================

@login_required
def attendance_kiosk(request):

    if request.user.role != 'kiosk':
        return HttpResponseForbidden(
            "Chỉ tài khoản trạm chấm công được truy cập."
        )

    context = {
        'active_menu': 'attendance',
    }

    return render(
        request,
        'attendance/kiosk.html',
        context
    )


# ============================================================
# 5. ĐĂNG KÝ KHUÔN MẶT BAN ĐẦU
# Chỉ quản lý được truy cập
# ============================================================

@login_required
def face_enrollment(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Chỉ quản lý được đăng ký khuôn mặt nhân viên."
        )

    danh_sach_nhan_vien = NhanVien.objects.all().order_by(
        'ho_ten'
    )

    return render(
        request,
        'attendance/face_enrollment.html',
        {
            'danh_sach_nhan_vien': danh_sach_nhan_vien,
            'active_menu': 'attendance',
        }
    )


# ============================================================
# 6. API LƯU MẪU FACE ID
# ============================================================

@login_required
@require_POST
def save_face_enrollment(request):

    if request.user.role != 'admin':
        return JsonResponse(
            {'success': False, 'message': 'Không có quyền truy cập.'},
            status=403
        )

    ma_nv = request.POST.get('ma_nv', '').strip()
    consent = request.POST.get('consent')
    image_file = request.FILES.get('image')

    if not ma_nv:
        return JsonResponse(
            {'success': False, 'message': 'Chưa chọn nhân viên.'},
            status=400
        )

    if consent != 'yes':
        return JsonResponse(
            {
                'success': False,
                'message': 'Chưa xác nhận đồng ý đăng ký Face ID.'
            },
            status=400
        )

    if not image_file:
        return JsonResponse(
            {'success': False, 'message': 'Chưa có ảnh khuôn mặt.'},
            status=400
        )

    if image_file.size > 2 * 1024 * 1024:
        return JsonResponse(
            {'success': False, 'message': 'Ảnh vượt quá 2 MB.'},
            status=400
        )

    if image_file.content_type not in ('image/jpeg', 'image/png'):
        return JsonResponse(
            {'success': False, 'message': 'Chỉ hỗ trợ ảnh JPEG hoặc PNG.'},
            status=400
        )

    nhan_vien = NhanVien.objects.filter(
        manv=ma_nv
    ).first()

    if nhan_vien is None:
        return JsonResponse(
            {'success': False, 'message': 'Không tìm thấy nhân viên.'},
            status=404
        )

    # Không tự động ghi đè mẫu đã đăng ký.
    if DuLieuKhuonMat.objects.filter(ma_nv=nhan_vien).exists():
        return JsonResponse(
            {
                'success': False,
                'message': (
                    'Nhân viên đã có Face ID. '
                    'Chức năng đăng ký lại sẽ được làm riêng.'
                )
            },
            status=409
        )

    try:
        image_bytes = image_file.read()

        embedding = create_face_embedding(image_bytes)
        encrypted_data = encrypt_embedding(embedding)

    except FaceProcessingError as error:
        return JsonResponse(
            {'success': False, 'message': str(error)},
            status=400
        )

    except cv2.error:
        return JsonResponse(
            {
                'success': False,
                'message': 'Mô hình nhận diện gặp lỗi xử lý ảnh.'
            },
            status=500
        )

    from django.db import IntegrityError, transaction

    try:
        with transaction.atomic():
            DuLieuKhuonMat.objects.create(
                ma_nv=nhan_vien,
                dl_ma_hoa=encrypted_data,
                dang_hoat_dong=True,
                ngay_dong_y=timezone.now(),
                phien_ban_mo_hinh=MODEL_VERSION,
            )

    except IntegrityError:
        return JsonResponse(
            {
                'success': False,
                'message': 'Nhân viên này đã có dữ liệu Face ID.'
            },
            status=409
        )

    return JsonResponse({
        'success': True,
        'message': (
            f'Đã đăng ký Face ID thành công cho '
            f'{nhan_vien.ho_ten}.'
        )}
    )


# ============================================================
# API XÁC MINH FACE ID TẠI TRẠM KIOSK
# Chưa thực hiện ghi dữ liệu chấm công
# ============================================================

@login_required
@require_POST
def verify_kiosk_face(request):

    # 1. Kiểm tra quyền trạm chấm công
    if request.user.role != 'kiosk':
        return JsonResponse({
            'success': False,
            'message': 'Tài khoản không có quyền xác minh Face ID.'
        }, status=403)

    # 2. Lấy dữ liệu gửi lên
    ma_nv = request.POST.get('ma_nv', '').strip()
    image_file = request.FILES.get('image')

    if not ma_nv or not image_file:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu mã nhân viên hoặc ảnh khuôn mặt.'
        }, status=400)

    if image_file.size > 2 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'message': 'Ảnh vượt quá dung lượng 2 MB.'
        }, status=400)

    if image_file.content_type not in (
        'image/jpeg', 'image/png'
    ):
        return JsonResponse({
            'success': False,
            'message': 'Chỉ hỗ trợ ảnh JPEG hoặc PNG.'
        }, status=400)

    # 3. Kiểm tra nhân viên và mẫu Face ID
    try:
        face_data = DuLieuKhuonMat.objects.select_related(
            'ma_nv'
        ).get(
            ma_nv_id=ma_nv,
            dang_hoat_dong=True
        )
    except DuLieuKhuonMat.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Nhân viên chưa có Face ID đang hoạt động.'
        }, status=404)

    if face_data.phien_ban_mo_hinh != MODEL_VERSION:
        return JsonResponse({
            'success': False,
            'message': 'Mẫu khuôn mặt không tương thích mô hình hiện tại.'
        }, status=409)

    # 4. Tạo embedding, giải mã và so khớp
    try:
        result = verify_face(
            image_file.read(),
            face_data.dl_ma_hoa
        )

    except FaceProcessingError:
        return JsonResponse({
            'success': False,
            'message': (
                'Không thể xác minh khuôn mặt. '
                'Vui lòng kiểm tra ảnh và cấu hình Face ID.'
            )
        }, status=400)

    except InvalidToken:
        return JsonResponse({
            'success': False,
            'message': 'Không thể xác minh dữ liệu Face ID.'
        }, status=400)

    # 5. Trả kết quả, chưa ghi chấm công
    if not result['matched']:
        return JsonResponse({
            'success': False,
            'matched': False,
            'message': (
                'Khuôn mặt không khớp với nhân viên đã chọn.'
            )
        })

    return JsonResponse({
        'success': True,
        'matched': True,
        'message': (
            'Đối chiếu khuôn mặt đạt ngưỡng thử nghiệm. '
            'Chưa ghi nhận chấm công.'
        )
    })


# ============================================================
# GIAI ĐOẠN 7: CHẤM CÔNG THẬT TẠI KIOSK
# ============================================================

def kiem_tra_tram(request):
    """
    Xác minh tài khoản kiosk và IP nguồn kết nối.
    Chưa phải giải pháp chứng minh vị trí tuyệt đối.
    """

    if request.user.role != 'kiosk':
        return None

    tram = TramChamCong.objects.filter(
        tai_khoan=request.user,
        dang_hoat_dong=True
    ).first()

    if tram is None:
        return None

    # Chỉ tin REMOTE_ADDR ở cấu hình demo trực tiếp.
    # Không lấy IP từ X-Forwarded-For do client gửi.
    ip_hien_tai = request.META.get('REMOTE_ADDR', '')

    # Yêu cầu phải cấu hình IP, không mặc định bỏ qua.
    if not tram.ip_cho_phep:
        return None

    if ip_hien_tai != tram.ip_cho_phep:
        return None

    return tram


def lay_gio_ca(lich):
    """
    Lấy giờ bắt đầu và kết thúc từ CaLamViec.
    """

    ca = lich.ma_ca_lam

    start_time = getattr(ca, 'start_time', None)
    end_time = getattr(ca, 'end_time', None)

    if start_time is None or end_time is None:
        raise ValueError(
            "Model CaLamViec chưa có trường giờ phù hợp."
        )

    bat_dau = timezone.make_aware(
        datetime.combine(lich.ngay_lam, start_time),
        timezone.get_current_timezone()
    )

    ket_thuc = timezone.make_aware(
        datetime.combine(lich.ngay_lam, end_time),
        timezone.get_current_timezone()
    )

    if ket_thuc <= bat_dau:
        ket_thuc += timedelta(days=1)

    return bat_dau, ket_thuc


# ============================================================
# API LẤY CA ĐÃ CÔNG BỐ TRONG NGÀY
# ============================================================

@login_required
def kiosk_today_shifts(request):

    if kiem_tra_tram(request) is None:
        return JsonResponse({
            'success': False,
            'message': 'Trạm chưa được cấp quyền hoặc mạng không hợp lệ.'
        }, status=403)

    ma_nv = request.GET.get('ma_nv', '').strip()

    if not ma_nv:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng nhập mã nhân viên.'
        }, status=400)

    nhan_vien = NhanVien.objects.filter(
        manv=ma_nv
    ).first()

    if nhan_vien is None:
        return JsonResponse({
            'success': False,
            'message': 'Không tìm thấy nhân viên.'
        }, status=404)

    hom_nay = timezone.localdate()

    lich_list = LichLamViec.objects.filter(
        ma_nv=nhan_vien,
        ngay_lam=hom_nay,
        is_published=True
    ).select_related('ma_ca_lam')

    du_lieu = []

    for lich in lich_list:

        try:
            bat_dau, ket_thuc = lay_gio_ca(lich)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Chưa cấu hình đúng thời gian ca làm.'
            }, status=500)

        cong = DuLieuChamCong.objects.filter(
            ma_lich_lam=lich
        ).first()

        if cong and cong.time_checkout:
            trang_thai = 'Đã Check-out'
        elif cong and cong.time_checkin:
            trang_thai = 'Đã Check-in'
        else:
            trang_thai = 'Chưa chấm công'

        du_lieu.append({
            'id': lich.pk,
            'ten_ca': lich.ma_ca_lam.ten_ca,
            'gio_bat_dau': bat_dau.strftime('%H:%M'),
            'gio_ket_thuc': ket_thuc.strftime('%H:%M'),
            'trang_thai': trang_thai
        })

    du_lieu.sort(key=lambda x: x['gio_bat_dau'])

    return JsonResponse({
        'success': True,
        'nhan_vien': nhan_vien.ho_ten,
        'ngay': hom_nay.strftime('%d/%m/%Y'),
        'ca_lam': du_lieu
    })


# ============================================================
# API XÁC MINH FACE ID VÀ GHI CHẤM CÔNG
# ============================================================

@login_required
@require_POST
def kiosk_record_attendance(request):

    # 1. Kiểm tra trạm
    tram = kiem_tra_tram(request)

    if tram is None:
        return JsonResponse({
            'success': False,
            'message': 'Trạm không hợp lệ hoặc sai mạng cho phép.'
        }, status=403)

    # 2. Lấy dữ liệu
    ma_nv = request.POST.get('ma_nv', '').strip()
    ma_lich_lam = request.POST.get('ma_lich_lam', '').strip()
    thao_tac = request.POST.get('thao_tac', '').strip()
    image_file = request.FILES.get('image')

    if thao_tac not in ['checkin', 'checkout']:
        return JsonResponse({
            'success': False,
            'message': 'Thao tác chấm công không hợp lệ.'
        }, status=400)

    if not ma_nv or not ma_lich_lam or not image_file:
        return JsonResponse({
            'success': False,
            'message': 'Thiếu mã nhân viên, ca làm hoặc ảnh.'
        }, status=400)

    if not ma_lich_lam.isdigit():
        return JsonResponse({
            'success': False,
            'message': 'Mã lịch làm không hợp lệ.'
        }, status=400)

    if image_file.size > 2 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'message': 'Ảnh vượt quá dung lượng 2 MB.'
        }, status=400)

    if image_file.content_type not in ('image/jpeg', 'image/png'):
        return JsonResponse({
            'success': False,
            'message': 'Chỉ hỗ trợ ảnh JPEG hoặc PNG.'
        }, status=400)

    # 3. Kiểm tra ca làm của đúng nhân viên
    hom_nay = timezone.localdate()

    lich = LichLamViec.objects.select_related(
        'ma_ca_lam'
    ).filter(
        pk=int(ma_lich_lam),
        ma_nv_id=ma_nv,
        ngay_lam=hom_nay,
        is_published=True
    ).first()

    if lich is None:
        return JsonResponse({
            'success': False,
            'message': 'Không tìm thấy ca đã công bố phù hợp.'
        }, status=404)

    try:
        bat_dau, ket_thuc = lay_gio_ca(lich)
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Thời gian ca làm chưa được cấu hình đúng.'
        }, status=500)

    # 4. Kiểm tra cửa sổ thời gian
    hien_tai = timezone.now()

    if thao_tac == 'checkin':
        som_nhat = bat_dau - timedelta(minutes=30)
        muon_nhat = bat_dau + timedelta(minutes=60)

        if not (som_nhat <= hien_tai <= muon_nhat):
            return JsonResponse({
                'success': False,
                'message': (
                    'Hiện chưa nằm trong khoảng thời gian '
                    'cho phép Check-in của ca này.'
                )
            }, status=400)

    else:
        muon_nhat = ket_thuc + timedelta(minutes=120)

        if not (bat_dau <= hien_tai <= muon_nhat):
            return JsonResponse({
                'success': False,
                'message': (
                    'Hiện chưa nằm trong khoảng thời gian '
                    'cho phép Check-out của ca này.'
                )
            }, status=400)

    # 5. Kiểm tra mẫu Face ID
    face_data = DuLieuKhuonMat.objects.filter(
        ma_nv_id=ma_nv,
        dang_hoat_dong=True
    ).first()

    if face_data is None:
        return JsonResponse({
            'success': False,
            'message': 'Nhân viên chưa có Face ID đang hoạt động.'
        }, status=404)

    if face_data.phien_ban_mo_hinh != MODEL_VERSION:
        return JsonResponse({
            'success': False,
            'message': 'Phiên bản mẫu Face ID không tương thích.'
        }, status=409)

    # 6. Xác minh ảnh tại chính yêu cầu ghi công
    try:
        ket_qua = verify_face(
            image_file.read(),
            face_data.dl_ma_hoa
        )

    except FaceProcessingError:
        return JsonResponse({
            'success': False,
            'message': 'Không xác minh được khuôn mặt. Vui lòng thử lại.'
        }, status=400)

    if not ket_qua['matched']:
        return JsonResponse({
            'success': False,
            'message': 'Khuôn mặt không khớp mẫu đã đăng ký.'
        }, status=403)

    # 7. Ghi công bằng transaction
    try:
        with transaction.atomic():

            cong = DuLieuChamCong.objects.select_for_update().filter(
                ma_lich_lam=lich
            ).first()

            # Thời gian ghi trên server, sau khi xác thực xong
            thoi_gian_ghi = timezone.now()
            ip = request.META.get('REMOTE_ADDR', '')

            if thao_tac == 'checkin':

                if cong is not None:
                    return JsonResponse({
                        'success': False,
                        'message': 'Ca này đã có bản ghi chấm công.'
                    }, status=409)

                cong = DuLieuChamCong.objects.create(
                    ma_lich_lam=lich,
                    time_checkin=thoi_gian_ghi,
                    ip_checkin=ip,
                    tram_checkin=tram,
                    trang_thai_cham_cong='Đã Check-in',
                    nguon_cham_cong='Face ID Kiosk'
                )

                thong_bao = 'Check-in thành công!'

            else:

                if cong is None or cong.time_checkin is None:
                    return JsonResponse({
                        'success': False,
                        'message': 'Bạn cần Check-in trước khi Check-out.'
                    }, status=409)

                if cong.time_checkout is not None:
                    return JsonResponse({
                        'success': False,
                        'message': 'Ca này đã Check-out.'
                    }, status=409)

                if thoi_gian_ghi <= cong.time_checkin:
                    return JsonResponse({
                        'success': False,
                        'message': 'Giờ Check-out phải sau giờ Check-in.'
                    }, status=409)

                cong.time_checkout = thoi_gian_ghi
                cong.ip_checkout = ip
                cong.tram_checkout = tram
                cong.trang_thai_cham_cong = 'Đã Check-out'

                cong.save(update_fields=[
                    'time_checkout',
                    'ip_checkout',
                    'tram_checkout',
                    'trang_thai_cham_cong'
                ])

                thong_bao = 'Check-out thành công!'

    except IntegrityError:
        return JsonResponse({
            'success': False,
            'message': 'Dữ liệu công vừa được cập nhật. Vui lòng tải lại.'
        }, status=409)

    return JsonResponse({
        'success': True,
        'message': thong_bao,
        'nhan_vien': lich.ma_nv.ho_ten,
        'ten_ca': lich.ma_ca_lam.ten_ca,
        'thao_tac': thao_tac,
        'thoi_gian': timezone.localtime(
            thoi_gian_ghi
        ).strftime('%H:%M:%S')
    })


# ============================================================
# TAB 2 - LỊCH SỬ VÀ TỔNG HỢP CÔNG QUẢN LÝ
# ============================================================

def lay_du_lieu_lich_su_quan_ly(request):

    hom_nay = timezone.localdate()
    thang_chon = request.GET.get(
        'month', hom_nay.strftime('%Y-%m')
    )
    tu_khoa = request.GET.get('q', '').strip()[:100]

    try:
        nam, thang = map(int, thang_chon.split('-'))
        if not (2000 <= nam <= 2100 and 1 <= thang <= 12):
            raise ValueError
    except (ValueError, AttributeError):
        nam, thang = hom_nay.year, hom_nay.month

    thang_chon = f'{nam:04d}-{thang:02d}'
    ngay_dau = date(nam, thang, 1)
    ngay_cuoi = date(
        nam, thang, calendar.monthrange(nam, thang)[1]
    )

    lich_qs = LichLamViec.objects.filter(
        ngay_lam__range=(ngay_dau, ngay_cuoi),
        is_published=True
    ).select_related('ma_nv', 'ma_ca_lam')

    if tu_khoa:
        lich_qs = lich_qs.filter(
            Q(ma_nv__ho_ten__icontains=tu_khoa) |
            Q(ma_nv__manv__icontains=tu_khoa)
        )

    lich_list = list(
        lich_qs.order_by(
            '-ngay_lam', 'ma_nv_id', 'ma_ca_lam_id'
        )
    )

    # Đọc dữ liệu chấm công một lần
    cong_map = {}

    for cong in DuLieuChamCong.objects.filter(
        ma_lich_lam__in=lich_list
    ).order_by('ma_cham_cong'):
        if cong.ma_lich_lam_id not in cong_map:
            cong_map[cong.ma_lich_lam_id] = cong

    chi_tiet = []
    tong_ca_hoan_thanh = 0
    tong_phut_lam = 0
    tong_luot_di_muon = 0
    tong_hop_map = {}

    for lich in lich_list:

        nv = lich.ma_nv
        ca = lich.ma_ca_lam
        cong = cong_map.get(lich.pk)

        checkin = cong.time_checkin if cong else None
        checkout = cong.time_checkout if cong else None

        try:
            bat_dau, ket_thuc = lay_gio_ca(lich)
        except ValueError:
            bat_dau, ket_thuc = None, None

        if checkin and checkout:
            trang_thai = 'Đã Check-out'
            mau_trang_thai = 'da-checkout'
        elif checkin:
            trang_thai = 'Đã Check-in'
            mau_trang_thai = 'da-checkin'
        elif checkout:
            trang_thai = 'Cần kiểm tra'
            mau_trang_thai = 'can-kiem-tra'
        elif lich.ngay_lam > hom_nay:
            trang_thai = 'Chưa đến ngày'
            mau_trang_thai = 'chua-den-ngay'
        else:
            trang_thai = 'Chưa chấm công'
            mau_trang_thai = 'chua-cham'

        # Tổng thời gian thực tế
        phut_lam = 0
        gio_thuc_te = '—'

        if checkin and checkout and checkout > checkin:
            phut_lam = int(
                (checkout - checkin).total_seconds() // 60
            )
            gio_thuc_te = (
                f'{phut_lam // 60}h {phut_lam % 60:02d}p'
            )
            tong_ca_hoan_thanh += 1
            tong_phut_lam += phut_lam

        # Tính số phút đi muộn, ngưỡng thử nghiệm 5 phút
        phut_muon = 0
        if checkin and bat_dau:
            phut_muon = max(
                0,
                int((checkin - bat_dau).total_seconds() // 60)
            )

        di_muon = phut_muon > 5

        # Về sớm: so với giờ kết thúc ca
        phut_ve_som = 0
        if checkout and ket_thuc:
            phut_ve_som = max(
                0,
                int((ket_thuc - checkout).total_seconds() // 60)
            )

        if di_muon:
            tong_luot_di_muon += 1

        ghi_chu_list = []

        if di_muon:
            ghi_chu_list.append(f'Muộn {phut_muon} phút')

        if phut_ve_som > 0:
            ghi_chu_list.append(f'Về sớm {phut_ve_som} phút')

        ghi_chu = ', '.join(ghi_chu_list) or '—'

        chi_tiet.append({
            'ngay_lam': lich.ngay_lam,
            'ma_nv': nv.pk,
            'ho_ten': nv.ho_ten,
            'ten_ca': ca.ten_ca,
            'bat_dau': bat_dau,
            'ket_thuc': ket_thuc,
            'checkin': checkin,
            'checkout': checkout,
            'gio_thuc_te': gio_thuc_te,
            'trang_thai': trang_thai,
            'mau_trang_thai': mau_trang_thai,
            'ghi_chu': ghi_chu,
        })

        # Tổng hợp theo từng nhân viên
        if nv.pk not in tong_hop_map:
            tong_hop_map[nv.pk] = {
                'ma_nv': nv.pk,
                'ho_ten': nv.ho_ten,
                'so_ca': 0,
                'ca_hoan_thanh': 0,
                'tong_phut': 0,
                'di_muon': 0,
            }

        item = tong_hop_map[nv.pk]
        item['so_ca'] += 1
        item['tong_phut'] += phut_lam

        if checkin and checkout:
            item['ca_hoan_thanh'] += 1

        if di_muon:
            item['di_muon'] += 1

    tong_hop = sorted(
        tong_hop_map.values(),
        key=lambda x: x['ho_ten'].lower()
    )

    for item in tong_hop:
        phut = item['tong_phut']
        item['tong_gio'] = (
            f'{phut // 60}h {phut % 60:02d}p'
        )

    return {
        'thang_chon': thang_chon,
        'tu_khoa': tu_khoa,
        'chi_tiet': chi_tiet,
        'tong_hop': tong_hop,
        'tong_luot_ca': len(chi_tiet),
        'tong_ca_hoan_thanh': tong_ca_hoan_thanh,
        'tong_gio': (
            f'{tong_phut_lam // 60}h '
            f'{tong_phut_lam % 60:02d}p'
        ),
        'tong_luot_di_muon': tong_luot_di_muon,
    }


@login_required
def manager_attendance_history(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Chỉ quản lý được xem lịch sử chấm công."
        )

    context = lay_du_lieu_lich_su_quan_ly(request)
    context['active_menu'] = 'attendance'

    return render(
        request,
        'attendance/manager_history.html',
        context
    )


# ============================================================
# XUẤT BÁO CÁO EXCEL
# ============================================================

@login_required
def manager_attendance_export(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Chỉ quản lý được xuất báo cáo chấm công."
        )

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    data = lay_du_lieu_lich_su_quan_ly(request)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Chi tiet cham cong'

    headers = [
        'Ngày làm', 'Mã NV', 'Nhân viên',
        'Ca làm', 'Giờ bắt đầu', 'Giờ kết thúc',
        'Check-in', 'Check-out', 'Giờ thực tế',
        'Trạng thái', 'Ghi chú'
    ]
    ws.append(headers)

    def excel_text(value):
        value = str(value)
        if value.startswith(('=', '+', '-', '@')):
            return "'" + value
        return value

    def dinh_dang_gio(value):
        if value is None:
            return ''
        return timezone.localtime(value).strftime('%H:%M:%S')

    for item in data['chi_tiet']:
        ws.append([
            item['ngay_lam'].strftime('%d/%m/%Y'),
            excel_text(item['ma_nv']),
            excel_text(item['ho_ten']),
            excel_text(item['ten_ca']),
            dinh_dang_gio(item['bat_dau']),
            dinh_dang_gio(item['ket_thuc']),
            dinh_dang_gio(item['checkin']),
            dinh_dang_gio(item['checkout']),
            item['gio_thuc_te'],
            item['trang_thai'],
            excel_text(item['ghi_chu']),
        ])

    # Sheet tổng hợp theo nhân viên
    ws2 = wb.create_sheet('Tong hop nhan vien')
    ws2.append([
        'Mã NV', 'Nhân viên', 'Số ca theo lịch',
        'Số ca hoàn thành', 'Tổng giờ', 'Lượt đi muộn'
    ])

    for item in data['tong_hop']:
        ws2.append([
            excel_text(item['ma_nv']),
            excel_text(item['ho_ten']),
            item['so_ca'],
            item['ca_hoan_thanh'],
            item['tong_gio'],
            item['di_muon'],
        ])

    # Định dạng nhẹ, đồng bộ Highlands
    for sheet in (ws, ws2):
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        sheet.row_dimensions[1].height = 28

        for cell in sheet[1]:
            cell.fill = PatternFill(
                fill_type='solid',
                fgColor='F8DFE4'
            )
            cell.font = Font(
                bold=True,
                color='80283A'
            )
            cell.alignment = Alignment(
                vertical='center'
            )

        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = 20

        sheet.column_dimensions['C'].width = 27

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )

    filename = (
        f"bao_cao_cham_cong_{data['thang_chon']}.xlsx"
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{filename}"'
    )

    wb.save(response)

    return response


# ============================================================
# TAB 4 - QUẢN LÝ FACE ID VÀ TRẠM CHẤM CÔNG
# ============================================================

@login_required
def manager_face_station(request):

    if request.user.role != 'admin':
        return HttpResponseForbidden(
            "Chỉ quản lý được truy cập Face ID và trạm."
        )

    # 1. Danh sách nhân viên
    nhan_vien_list = list(
        NhanVien.objects.all().order_by('ho_ten')
    )

    # 2. Các mẫu khuôn mặt đã đăng ký
    face_list = DuLieuKhuonMat.objects.all()
    face_map = {
        face.ma_nv_id: face
        for face in face_list
    }

    # 3. Trạng thái Face ID từng nhân viên
    danh_sach_face = []
    so_da_dang_ky = 0
    so_dang_hoat_dong = 0

    for nv in nhan_vien_list:

        face = face_map.get(nv.pk)

        if face is None:
            trang_thai = 'Chưa đăng ký'
            mau_trang_thai = 'chua-dang-ky'
            ngay_cap_nhat = None
            phien_ban = '—'
            so_sanh_duoc = False

        else:
            so_da_dang_ky += 1

            ngay_cap_nhat = face.ngay_cap_nhat
            phien_ban = face.phien_ban_mo_hinh

            if face.dang_hoat_dong:
                trang_thai = 'Đang hoạt động'
                mau_trang_thai = 'dang-hoat-dong'
                so_dang_hoat_dong += 1
                so_sanh_duoc = True
            else:
                trang_thai = 'Đã khóa'
                mau_trang_thai = 'da-khoa'
                so_sanh_duoc = False

        danh_sach_face.append({
            'ma_nv': nv.pk,
            'ho_ten': nv.ho_ten,
            'trang_thai': trang_thai,
            'mau_trang_thai': mau_trang_thai,
            'ngay_cap_nhat': ngay_cap_nhat,
            'phien_ban': phien_ban,
            'so_sanh_duoc': so_sanh_duoc,
        })

    # 4. Danh sách trạm trong database
    tram_list = list(
        TramChamCong.objects.all().order_by('ma_tram')
    )

    danh_sach_tram = []
    so_tram_hoat_dong = 0

    for tram in tram_list:

        if tram.dang_hoat_dong:
            so_tram_hoat_dong += 1

        tai_khoan = getattr(tram, 'tai_khoan', None)

        danh_sach_tram.append({
            'ma_tram': tram.pk,
            'ten_tram': tram.ten_tram,
            'chi_nhanh': tram.chi_nhanh,
            'ip_cho_phep': tram.ip_cho_phep,
            'tai_khoan': (
                tai_khoan.username if tai_khoan else 'Chưa liên kết'
            ),
            'dang_hoat_dong': tram.dang_hoat_dong,
        })

    context = {
        'active_menu': 'attendance',
        'tong_nhan_vien': len(nhan_vien_list),
        'so_da_dang_ky': so_da_dang_ky,
        'so_chua_dang_ky': (
            len(nhan_vien_list) - so_da_dang_ky
        ),
        'so_dang_hoat_dong': so_dang_hoat_dong,
        'tong_tram': len(tram_list),
        'so_tram_hoat_dong': so_tram_hoat_dong,
        'danh_sach_face': danh_sach_face,
        'danh_sach_tram': danh_sach_tram,
    }

    return render(
        request,
        'attendance/manager_face_station.html',
        context
    )
