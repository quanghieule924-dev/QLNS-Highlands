import re
import uuid
from datetime import date, time, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from employees.models import NhanVien
from .models import ChuongTrinhTapSu, TienDoTapSu, KetQuaThi, KhungChuongTrinh,BaiHocKhungMau, BaiHoc, LichThi, DeThi, CauHoi
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .exam_utils import tao_de_random
from .exam_flow import lay_trang_thai_thi

# ----------------------------------------------------
# 1. HÀM HIỂN THỊ MAIN DASHBOARD & BỘ LỌC
# ----------------------------------------------------
GIO_CA_THI = {
    'Sang': (9, 0, 10, 0),
    'Chieu': (12, 0, 15, 0),
    'Toi': (19, 0, 20, 0),

    # Hỗ trợ dữ liệu cũ đã lưu tên đầy đủ
    'Ca Sáng (09:00 - 10:00)': (9, 0, 10, 0),
    'Ca Chiều (12:00 - 15:00)': (12, 0, 15, 0),
    'Ca Tối (19:00 - 20:00)': (19, 0, 20, 0),
}


def xac_dinh_trang_thai_thi(lich_thi, de_thi):

    if lich_thi is None:
        return 'chua_co_lich', False

    ca = GIO_CA_THI.get(
        (lich_thi.ca_thi or '').strip()
    )

    if ca is None:
        return 'ca_khong_hop_le', False

    gio_bd, phut_bd, gio_kt, phut_kt = ca

    mui_gio = timezone.get_current_timezone()

    bat_dau = timezone.make_aware(
        datetime.combine(
            lich_thi.ngay_thi,
            time(gio_bd, phut_bd)
        ),
        mui_gio
    )

    ket_thuc = timezone.make_aware(
        datetime.combine(
            lich_thi.ngay_thi,
            time(gio_kt, phut_kt)
        ),
        mui_gio
    )

    hien_tai = timezone.now()

    if hien_tai < bat_dau:
        return 'chua_den_gio', False

    if hien_tai >= ket_thuc:
        return 'het_ca_thi', False

    if de_thi is None:
        return 'chua_co_de', False

    if not CauHoi.objects.filter(ma_dt=de_thi).exists():
        return 'chua_co_de', False

    return 'duoc_lam_bai', True



@login_required
def dashboard_quan_ly_tap_su(request):

    # ==========================================
    # 1. PHÂN QUYỀN QUẢN LÝ
    # ==========================================

    if not (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied

    # ==========================================
    # 2. LẤY DANH SÁCH NHÂN VIÊN TẬP SỰ
    # ==========================================

    base_qs = (
        ChuongTrinhTapSu.objects
        .select_related('ma_nv', 'ma_khung')
        .filter(
            ma_nv__trang_thai__in=[
                'Tập sự',
                'Tap_su'
            ]
        )
        .order_by('ma_nv__ho_ten', 'ma_ct')
    )

    danh_sach_goc = []

    # ==========================================
    # 3. XÁC ĐỊNH TRẠNG THÁI TỪNG NHÂN VIÊN
    # ==========================================

    for ct in base_qs:

        nhan_vien = ct.ma_nv

        # Lấy trạng thái thi từ kết quả đã lưu
        thong_tin_thi = lay_trang_thai_thi(
            nhan_vien
        )
        # Chuẩn hóa trạng thái trả về từ exam_flow.py
        trang_thai_goc = str(
            thong_tin_thi.get('trang_thai') or ''
        ).strip().casefold()

        if trang_thai_goc in ('dat', 'thi_dat'):
            ct.trang_thai_thi = 'thi_dat'

        elif trang_thai_goc in (
                'khongdat',
                'khong_dat',
                'thi_khong_dat'
        ):
            ct.trang_thai_thi = 'thi_khong_dat'

        elif trang_thai_goc in ('daxeplich', 'da_xep_lich'):
            ct.trang_thai_thi = 'da_xep_lich'

        else:
            ct.trang_thai_thi = trang_thai_goc

        ct.lich_thi_hien_tai = thong_tin_thi[
            'lich_thi'
        ]

        ct.ket_qua_thi = thong_tin_thi.get(
            'ket_qua'
        )

        # ------------------------------
        # Chờ duyệt chương trình
        # ------------------------------

        # ======================================
        # XÁC ĐỊNH GIAI ĐOẠN ĐÀO TẠO
        # ======================================

        ket_qua_thi = thong_tin_thi.get('ket_qua')

        trang_thai_thi = str(
            thong_tin_thi.get('trang_thai') or ''
        ).strip().casefold()

        # Đã thi đạt: ưu tiên chuyển hồ sơ
        da_thi_dat = (
            trang_thai_thi in ('dat', 'thi_dat')
            or (
                isinstance(ket_qua_thi, dict)
                and ket_qua_thi.get('dat') is True
            )
        )

        if ct.trang_thai_duyet == 'Chờ duyệt':
            ct.giai_doan = 'cho_duyet'

        elif ct.trang_thai_duyet != 'Đã duyệt':
            ct.giai_doan = 'khac'

        elif ct.tong_tien_do < 100:
            ct.giai_doan = 'dang_ojt'

        elif da_thi_dat:
            ct.giai_doan = 'cho_chuyen_ho_so'

        elif (
            trang_thai_thi in (
                'khongdat',
                'khong_dat',
                'thi_khong_dat',
            )
            or (
                isinstance(ket_qua_thi, dict)
                and ket_qua_thi.get('dat') is False
            )
        ):
            ct.giai_doan = 'thi_lai'

        elif not thong_tin_thi.get(
            'duoc_bo_tri_thi', True
        ):
            ct.giai_doan = 'da_xep_lich'

        else:
            ct.giai_doan = 'du_dieu_kien'

        danh_sach_goc.append(ct)

    # ==========================================
    # 4. THỐNG KÊ DASHBOARD
    # ==========================================

    def dem_nhan_vien(ds):
        return len({
            ct.ma_nv_id
            for ct in ds
        })

    # Tổng nhân viên đang trong quy trình tập sự
    tong_so_tap_su = dem_nhan_vien(
        danh_sach_goc
    )

    # Chưa duyệt chương trình
    cho_duyet_lo_trinh = dem_nhan_vien([
        ct for ct in danh_sach_goc
        if ct.giai_doan == 'cho_duyet'
    ])

    # Đang học OJT
    dang_thuc_hanh_ojt = dem_nhan_vien([
        ct for ct in danh_sach_goc
        if ct.giai_doan == 'dang_ojt'
    ])

    # Đủ điều kiện bố trí thi hoặc thi lại
    du_dieu_kien_thi = dem_nhan_vien([
        ct for ct in danh_sach_goc
        if ct.giai_doan in (
            'du_dieu_kien',
            'thi_lai'
        )
    ])

    # Đã đạt và chờ chuyển hồ sơ
    cho_chuyen_ho_so = dem_nhan_vien([
        ct for ct in danh_sach_goc
        if ct.giai_doan == 'cho_chuyen_ho_so'
    ])

    # ==========================================
    # 5. LẤY THÔNG TIN BỘ LỌC
    # ==========================================

    search_query = request.GET.get(
        'search', ''
    ).strip()

    vi_tri = request.GET.get(
        'vi_tri', ''
    ).strip()

    trang_thai_filter = request.GET.get(
        'trang_thai', ''
    ).strip()

    stat = request.GET.get(
        'stat', ''
    ).strip()

    danh_sach = danh_sach_goc

    # ==========================================
    # 6. TÌM KIẾM THEO TÊN / MÃ NHÂN VIÊN
    # ==========================================

    if search_query:

        tu_khoa = search_query.casefold()

        danh_sach = [
            ct for ct in danh_sach
            if (
                tu_khoa in (
                    ct.ma_nv.ho_ten or ''
                ).casefold()

                or tu_khoa in (
                    ct.ma_nv.manv or ''
                ).casefold()
            )
        ]

    # ==========================================
    # 7. LỌC THEO VỊ TRÍ
    # ==========================================

    if vi_tri:

        danh_sach = [
            ct for ct in danh_sach
            if ct.ma_nv.vi_tri == vi_tri
        ]

    # ==========================================
    # 8. LỌC THEO TRẠNG THÁI
    # ==========================================

    trang_thai_map = {
        'Chờ duyệt': 'cho_duyet',
        'Đang OJT': 'dang_ojt',
        'Đã xếp lịch thi': 'da_xep_lich',
        'Đã xếp lịch': 'da_xep_lich',
        'Thi không đạt': 'thi_lai',
        'Chờ chuyển hồ sơ': 'cho_chuyen_ho_so',
    }

    if trang_thai_filter == 'Đủ điều kiện thi':

        danh_sach = [
            ct for ct in danh_sach
            if ct.giai_doan in (
                'du_dieu_kien',
                'thi_lai'
            )
        ]

    elif trang_thai_filter in trang_thai_map:

        giai_doan = trang_thai_map[
            trang_thai_filter
        ]

        danh_sach = [
            ct for ct in danh_sach
            if ct.giai_doan == giai_doan
        ]

    # ==========================================
    # 9. LỌC KHI BẤM VÀO THẺ THỐNG KÊ
    # ==========================================

    if stat == 'cho_duyet':

        danh_sach = [
            ct for ct in danh_sach
            if ct.giai_doan == 'cho_duyet'
        ]

    elif stat == 'dang_ojt':

        danh_sach = [
            ct for ct in danh_sach
            if ct.giai_doan == 'dang_ojt'
        ]

    elif stat == 'du_dieu_kien':

        danh_sach = [
            ct for ct in danh_sach
            if ct.giai_doan in (
                'du_dieu_kien',
                'thi_lai'
            )
        ]

    elif stat == 'cho_chuyen_ho_so':

        danh_sach = [
            ct for ct in danh_sach
            if ct.giai_doan == 'cho_chuyen_ho_so'
        ]

    # ==========================================
    # 10. TRUYỀN DỮ LIỆU CHO TEMPLATE
    # ==========================================

    context = {
        'active_menu': 'training',

        'tong_so_tap_su': tong_so_tap_su,

        'cho_duyet_lo_trinh': cho_duyet_lo_trinh,

        'dang_thuc_hanh_ojt': dang_thuc_hanh_ojt,

        'du_dieu_kien_thi': du_dieu_kien_thi,

        'cho_chuyen_ho_so': cho_chuyen_ho_so,

        'danh_sach_tap_su': danh_sach,

        'search_query': search_query,

        'vi_tri_selected': vi_tri,

        'trang_thai_selected': trang_thai_filter,

        'current_stat': stat,
    }

    return render(
        request,
        'training/dashboard.html',
        context
    )


# 3. HÀM HIỂN THỊ KẾT QUẢ THI
# ----------------------------------------------------

@login_required
def ket_qua_thi(request, ma_kq):

    ket_qua = get_object_or_404(
        KetQuaThi.objects.select_related(
            'ma_lt__ma_nv'
        ),
        pk=ma_kq
    )

    la_quan_ly = (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    )

    la_chu_so_huu = (
        getattr(request.user, 'role', None) == 'employee'
        and ket_qua.ma_lt.ma_nv.tai_khoan_id == request.user.pk
    )

    if not (la_quan_ly or la_chu_so_huu):
        raise PermissionDenied(
            'Bạn không có quyền xem kết quả thi này.'
        )

    return render(
        request,
        'training/ket_qua_thi.html',
        {'ket_qua': ket_qua}
    )


@login_required
def duyet_chuong_trinh(request, pk):

    if not (
        request.user.is_superuser
        or getattr(request.user, "role", None) == "admin"
    ):
        raise PermissionDenied

    # Lấy chương trình từ database
    chuong_trinh = get_object_or_404(
        ChuongTrinhTapSu.objects.select_related(
            'ma_nv',
            'ma_khung'
        ),
        pk=pk
    )

    # Xử lý khi quản lý nhấn Phê duyệt
    if request.method == 'POST':

        action = request.POST.get('action')

        if action == 'phe_duyet':

            with transaction.atomic():

                ct = (
                    ChuongTrinhTapSu.objects
                    .select_for_update()
                    .get(pk=pk)
                )

                if ct.trang_thai_duyet == 'Đã duyệt':
                    messages.info(
                        request,
                        'Chương trình này đã được phê duyệt.'
                    )

                elif not BaiHoc.objects.filter(
                    ma_ct=ct
                ).exists():
                    messages.error(
                        request,
                        'Chương trình chưa có bài học.'
                    )

                else:
                    ct.trang_thai_duyet = 'Đã duyệt'
                    ct.save(
                        update_fields=['trang_thai_duyet']
                    )

                    messages.success(
                        request,
                        'Phê duyệt chương trình thành công!'
                    )

            return redirect(
                'training:duyet_chuong_trinh',
                pk=pk
            )

    # ======================================
    # PHẦN HIỂN THỊ GIAO DIỆN
    # PHẢI NẰM NGOÀI IF POST
    # ======================================

    ds_bai_hoc = BaiHoc.objects.filter(
        ma_ct=chuong_trinh
    ).order_by(
        'buoi_hoc',
        'ma_bh'
    )

    tong_so_bai = ds_bai_hoc.count()

    tong_phut = (
        ds_bai_hoc.aggregate(
            tong=Sum('thoi_gian_hoc')
        )['tong'] or 0
    )

    tong_gio = round(tong_phut / 60, 1)

    context = {
        'active_menu': 'training',
        'chuong_trinh': chuong_trinh,
        'ds_bai_hoc': ds_bai_hoc,
        'tong_so_bai': tong_so_bai,
        'tong_gio': tong_gio,
    }

    # Dòng này phải ở cùng mức thụt lề
    # với if request.method == 'POST'
    return render(
        request,
        'training/duyet_chuong_trinh.html',
        context
    )

# ----------------------------------------------------
# 4. HÀM THAO TÁC: DUYỆT LỘ TRÌNH
# ----------------------------------------------------

@login_required
def duyet_lo_trinh(request, ma_ct):

    # 1. Kiểm tra quyền quản lý / superuser
    if not (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied(
            'Chỉ quản lý được duyệt lộ trình đào tạo.'
        )

    # 2. Chỉ cho phép duyệt bằng phương thức POST
    if request.method != 'POST':
        return redirect(
            'training:duyet_chuong_trinh',
            pk=ma_ct
        )

    # 3. Lấy chương trình cần duyệt
    chuong_trinh = get_object_or_404(
        ChuongTrinhTapSu,
        pk=ma_ct
    )

    # 4. Kiểm tra chương trình có bài học chưa
    if not BaiHoc.objects.filter(
        ma_ct=chuong_trinh
    ).exists():
        messages.error(
            request,
            'Chương trình chưa có bài học nên không thể duyệt.'
        )
        return redirect(
            'training:duyet_chuong_trinh',
            pk=ma_ct
        )

    # 5. Nếu chương trình đã duyệt
    if chuong_trinh.trang_thai_duyet == 'Đã duyệt':
        messages.info(
            request,
            'Chương trình này đã được phê duyệt trước đó.'
        )
        return redirect(
            'training:duyet_chuong_trinh',
            pk=ma_ct
        )

    # 6. Cập nhật trạng thái duyệt
    chuong_trinh.trang_thai_duyet = 'Đã duyệt'
    chuong_trinh.save(
        update_fields=['trang_thai_duyet']
    )

    messages.success(
        request,
        f'Đã duyệt lộ trình đào tạo cho nhân viên '
        f'{chuong_trinh.ma_nv.ho_ten}!'
    )

    return redirect(
        'training:dashboard_quan_ly_tap_su'
    )

# ----------------------------------------------------
# 5. HÀM THAO TÁC: TÍCH CHECKLIST TĂNG TIẾN ĐỘ OJT
# ----------------------------------------------------

@login_required
def cap_nhat_tien_do_ojt(request, ma_nv):

    # 1. Chỉ quản lý được đánh giá OJT

    if not (
            request.user.is_superuser
            or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied(
            'Chỉ quản lý được đánh giá OJT.'
        )

    # 2. Lấy chương trình đã duyệt của nhân viên
    chuong_trinh = (
        ChuongTrinhTapSu.objects
        .select_related('ma_nv', 'ma_khung')
        .filter(
            ma_nv__manv=ma_nv,
            trang_thai_duyet='Đã duyệt'
        )
        .order_by('-ma_ct')
        .first()
    )

    if chuong_trinh is None:
        raise Http404(
            'Nhân viên chưa có chương trình OJT được duyệt.'
        )

    nhan_vien = chuong_trinh.ma_nv

    # 3. Lấy bài học từ chương trình thật
    ds_bai_hoc = list(
        BaiHoc.objects.filter(
            ma_ct=chuong_trinh
        ).order_by('buoi_hoc', 'ma_bh')
    )

    # 4. Hàm lấy kết quả đánh giá đã lưu
    def lay_tien_do():
        ket_qua = {}

        ds = TienDoTapSu.objects.filter(
            ma_nv=nhan_vien,
            ma_bh__in=ds_bai_hoc
        ).order_by('ngay_danh_gia', 'ma_td')

        for td in ds:
            ket_qua[td.ma_bh_id] = td

        return ket_qua

    # ==========================================
    # XỬ LÝ LƯU CHECKLIST
    # ==========================================
    if request.method == 'POST':

        action = request.POST.get('action')

        if action not in ('luu_tam', 'xac_nhan'):
            messages.error(
                request,
                'Thao tác không hợp lệ.'
            )
            return redirect(
                'training:cap_nhat_tien_do_ojt',
                ma_nv=ma_nv
            )

        du_lieu = []

        # 5. Kiểm tra toàn bộ dữ liệu trước khi lưu
        try:
            for bai in ds_bai_hoc:

                ma_bh = bai.ma_bh

                trang_thai = request.POST.get(
                    f'trang_thai_{ma_bh}', ''
                ).strip()

                ngay_text = request.POST.get(
                    f'ngay_{ma_bh}', ''
                ).strip()

                nhan_xet = request.POST.get(
                    f'nhan_xet_{ma_bh}', ''
                ).strip()

                if trang_thai not in (
                    '',
                    'Đạt',
                    'Chưa đạt'
                ):
                    raise ValueError(
                        'Trạng thái đánh giá không hợp lệ.'
                    )

                if len(nhan_xet) > 2000:
                    raise ValueError(
                        'Nhận xét không được quá 2000 ký tự.'
                    )

                # Bài chưa đánh giá không có ngày đánh giá
                ngay_danh_gia = None

                if trang_thai:
                    if not ngay_text:
                        raise ValueError(
                            f'Vui lòng chọn ngày đánh giá '
                            f'cho bài {bai.ten_bh}.'
                        )

                    ngay_danh_gia = date.fromisoformat(
                        ngay_text
                    )

                    if ngay_danh_gia > date.today():
                        raise ValueError(
                            'Ngày đánh giá không được '
                            'lớn hơn ngày hiện tại.'
                        )

                du_lieu.append({
                    'bai': bai,
                    'trang_thai': trang_thai,
                    'ngay': ngay_danh_gia,
                    'nhan_xet': nhan_xet,
                })

        except ValueError as error:
            messages.error(
                request,
                f'Dữ liệu không hợp lệ: {error}'
            )
            return redirect(
                'training:cap_nhat_tien_do_ojt',
                ma_nv=ma_nv
            )

        nhan_xet_chung = request.POST.get(
            'nhan_xet_chung', ''
        ).strip()

        if len(nhan_xet_chung) > 5000:
            messages.error(
                request,
                'Nhận xét chung quá dài.'
            )
            return redirect(
                'training:cap_nhat_tien_do_ojt',
                ma_nv=ma_nv
            )

        # ==========================================
        # LƯU VÀO DATABASE
        # ==========================================
        with transaction.atomic():

            # Khóa chương trình trong quá trình lưu
            ct = ChuongTrinhTapSu.objects.select_for_update().get(
                pk=chuong_trinh.pk
            )

            if ct.trang_thai_duyet != 'Đã duyệt':
                raise PermissionDenied

            tien_do_cu = lay_tien_do()

            for item in du_lieu:

                bai = item['bai']

                td = tien_do_cu.get(bai.ma_bh)

                # Nếu chưa có bản ghi tiến độ thì tạo mới
                if td is None:

                    # Không tạo bản ghi trống không cần thiết
                    if (
                        not item['trang_thai']
                        and not item['nhan_xet']
                    ):
                        continue

                    td = TienDoTapSu(
                        ma_td='TD' + uuid.uuid4().hex[:16],
                        ma_nv=nhan_vien,
                        ma_bh=bai,
                    )

                td.trang_thai_danh_gia = (
                    item['trang_thai'] or None
                )
                td.ngay_danh_gia = item['ngay']
                td.nhan_xet = item['nhan_xet']

                td.save()

            # 6. Tính lại tiến độ bằng dữ liệu đã lưu
            tien_do_moi = lay_tien_do()

            tong_bai = len(ds_bai_hoc)

            so_bai_dat = sum(
                1
                for bai in ds_bai_hoc
                if (
                    bai.ma_bh in tien_do_moi
                    and tien_do_moi[
                        bai.ma_bh
                    ].trang_thai_danh_gia == 'Đạt'
                )
            )

            phan_tram = (
                round(so_bai_dat * 100 / tong_bai, 1)
                if tong_bai else 0
            )

            # 7. Cập nhật phần trăm chương trình
            ct.tong_tien_do = phan_tram
            ct.nhan_xet_chung = nhan_xet_chung

            ct.save(update_fields=[
                'tong_tien_do',
                'nhan_xet_chung',
            ])

        # 8. Thông báo kết quả
        if action == 'xac_nhan':
            messages.success(
                request,
                'Đã xác nhận và lưu kết quả OJT. '
                f'Tiến độ hiện tại: {phan_tram}%.'
            )
        else:
            messages.success(
                request,
                'Đã lưu tiến độ OJT thành công.'
            )

        return redirect(
            'training:cap_nhat_tien_do_ojt',
            ma_nv=ma_nv
        )

    # ==========================================
    # GET: HIỂN THỊ CHECKLIST
    # ==========================================

    tien_do_da_luu = lay_tien_do()

    cac_buoi = {}
    so_bai_dat = 0

    for bai in ds_bai_hoc:

        so_buoi = bai.buoi_hoc or 0

        if so_buoi not in cac_buoi:
            cac_buoi[so_buoi] = {
                'so': so_buoi,
                'bai_hoc': [],
                'so_bai': 0,
                'so_bai_dat': 0,
            }

        td = tien_do_da_luu.get(bai.ma_bh)

        trang_thai = (
            td.trang_thai_danh_gia
            if td else ''
        ) or ''

        if trang_thai == 'Đạt':
            so_bai_dat += 1
            cac_buoi[so_buoi]['so_bai_dat'] += 1

        cac_buoi[so_buoi]['so_bai'] += 1

        cac_buoi[so_buoi]['bai_hoc'].append({
            'ma_bh': bai.ma_bh,
            'ten': bai.ten_bh,
            'loai': bai.loai_bh,
            'thoi_luong': bai.thoi_gian_hoc,
            'trang_thai': trang_thai,
            'ngay': td.ngay_danh_gia if td else None,
            'nhan_xet': td.nhan_xet if td else '',
        })

    danh_sach_buoi = list(cac_buoi.values())

    # Trạng thái và tỷ lệ từng buổi
    for buoi in danh_sach_buoi:

        buoi['phan_tram'] = (
            round(
                buoi['so_bai_dat'] * 100 /
                buoi['so_bai'],
                1
            )
            if buoi['so_bai'] else 0
        )

    tong_bai = len(ds_bai_hoc)

    tien_do = (
        round(so_bai_dat * 100 / tong_bai, 1)
        if tong_bai else 0
    )

    context = {
        'active_menu': 'training',
        'nhan_vien': nhan_vien,
        'chuong_trinh': chuong_trinh,
        'cac_buoi': danh_sach_buoi,
        'tong_bai': tong_bai,
        'so_bai_dat': so_bai_dat,
        'tien_do': tien_do,
        'nhan_xet_chung': (
            chuong_trinh.nhan_xet_chung or ''
        ),
    }

    return render(
        request,
        'training/check_ojt.html',
        context
    )

# ----------------------------------------------------
# 6. HÀM THAO TÁC: BỐ TRÍ THI TỔNG KẾT
# ----------------------------------------------------


@login_required
def bo_tri_thi(request, ma_nv):

    if not (
        request.user.is_superuser
        or getattr(request.user, "role", None) == "admin"
    ):
        raise PermissionDenied

    CA_THI = {
        "Sang": "Ca Sáng (09:00 - 10:00)",
        "Chieu": "Ca Chiều (12:00 - 15:00)",
        "Toi": "Ca Tối (19:00 - 20:00)",
    }

    chuong_trinh = (
        ChuongTrinhTapSu.objects
        .select_related("ma_nv", "ma_khung")
        .filter(
            ma_nv__manv=ma_nv,
            trang_thai_duyet="Đã duyệt",
            ma_nv__trang_thai__in=["Tập sự", "Tap_su"],
        )
        .order_by("-ma_ct")
        .first()
    )

    if chuong_trinh is None:
        messages.error(
            request,
            "Không tìm thấy chương trình OJT đang xử lý."
        )
        return redirect(
            "training:dashboard_quan_ly_tap_su"
        )

    nhan_vien = chuong_trinh.ma_nv

    # ===============================
    # KIỂM TRA OJT 100%
    # ===============================

    ds_bai_hoc = list(
        BaiHoc.objects.filter(
            ma_ct=chuong_trinh
        ).order_by("buoi_hoc", "ma_bh")
    )

    tong_bai = len(ds_bai_hoc)

    tien_do_theo_bai = {}

    ds_danh_gia = (
        TienDoTapSu.objects
        .filter(
            ma_nv=nhan_vien,
            ma_bh__in=ds_bai_hoc
        )
        .order_by("ngay_danh_gia", "ma_td")
    )

    for item in ds_danh_gia:
        tien_do_theo_bai[item.ma_bh_id] = item

    so_bai_dat = sum(
        1
        for bai in ds_bai_hoc
        if (
            bai.ma_bh in tien_do_theo_bai
            and (
                tien_do_theo_bai[bai.ma_bh]
                .trang_thai_danh_gia or ""
            ).strip().casefold() == "đạt"
        )
    )

    phan_tram = (
        round(so_bai_dat * 100 / tong_bai, 1)
        if tong_bai else 0
    )

    if tong_bai == 0 or so_bai_dat != tong_bai:
        messages.error(
            request,
            "Nhân viên chưa hoàn thành 100% OJT."
        )
        return redirect(
            "training:dashboard_quan_ly_tap_su"
        )

    ngay_hoan_thanh = max(
        (
            td.ngay_danh_gia
            for td in tien_do_theo_bai.values()
            if td.ngay_danh_gia is not None
        ),
        default=None
    )

    # ===============================
    # KIỂM TRA TRẠNG THÁI THI
    # ===============================

    thong_tin = lay_trang_thai_thi(nhan_vien)

    if not thong_tin["duoc_bo_tri_thi"]:
        messages.warning(
            request,
            "Nhân viên đã có lịch thi hoặc đã thi đạt."
        )
        return redirect(
            "training:dashboard_quan_ly_tap_su"
        )

    lich_thi_da_co = (
        LichThi.objects
        .filter(ma_nv=nhan_vien)
        .exclude(ma_lt__startswith="BANKLT")
        .order_by("-ngay_thi", "-ma_lt")
    )

    ds_de_thi = (
        DeThi.objects
        .filter(cauhoi__isnull=False)
        .distinct()
        .order_by("ten_de_thi", "ma_dt")
    )

    # ===============================
    # QUẢN LÝ XÁC NHẬN LỊCH
    # ===============================

    if request.method == "POST":

        ngay_thi_text = request.POST.get(
            "ngay_thi", ""
        ).strip()

        ca_thi = request.POST.get(
            "ca_thi", ""
        ).strip()

        try:
            ngay_thi = date.fromisoformat(
                ngay_thi_text
            )
        except ValueError:
            messages.error(
                request,
                "Ngày thi không hợp lệ."
            )
            return redirect(
                "training:bo_tri_thi",
                ma_nv=ma_nv
            )

        if ngay_thi < timezone.localdate():
            messages.error(
                request,
                "Không được xếp lịch thi trong quá khứ."
            )
            return redirect(
                "training:bo_tri_thi",
                ma_nv=ma_nv
            )

        if ca_thi not in CA_THI:
            messages.error(
                request,
                "Ca thi không hợp lệ."
            )
            return redirect(
                "training:bo_tri_thi",
                ma_nv=ma_nv
            )

        # ===============================
        # TẠO LỊCH TRONG TRANSACTION
        # ===============================

        try:
            with transaction.atomic():

                nv_khoa = (
                    NhanVien.objects
                    .select_for_update()
                    .get(pk=nhan_vien.pk)
                )

                ct_khoa = (
                    ChuongTrinhTapSu.objects
                    .select_for_update()
                    .get(pk=chuong_trinh.pk)
                )

                if (
                    nv_khoa.trang_thai not in ("Tập sự", "Tap_su")
                    or ct_khoa.trang_thai_duyet != "Đã duyệt"
                ):
                    raise ValueError(
                        "Chương trình không còn đủ điều kiện."
                    )

                # Kiểm tra lại tiến độ đã lưu.
                bai_ids = [b.ma_bh for b in ds_bai_hoc]

                danh_gia_moi = {}
                for td in (
                    TienDoTapSu.objects
                    .filter(
                        ma_nv=nv_khoa,
                        ma_bh_id__in=bai_ids
                    )
                    .order_by("ngay_danh_gia", "ma_td")
                ):
                    danh_gia_moi[td.ma_bh_id] = td

                if any(
                    bai_id not in danh_gia_moi
                    or (
                        danh_gia_moi[bai_id]
                        .trang_thai_danh_gia or ""
                    ).strip().casefold() != "đạt"
                    for bai_id in bai_ids
                ):
                    raise ValueError(
                        "OJT chưa hoàn thành 100%."
                    )

                # Kiểm tra lần nữa trước khi lưu.
                trang_thai_moi = lay_trang_thai_thi(
                    nv_khoa
                )

                if not trang_thai_moi["duoc_bo_tri_thi"]:
                    raise ValueError(
                        "Đã có lịch thi hoặc đã thi đạt."
                    )

                lich_truoc = trang_thai_moi["lich_thi"]

                # Thi lại phải sau lần thi trước.
                if (
                    trang_thai_moi["la_thi_lai"]
                    and lich_truoc is not None
                    and ngay_thi <= lich_truoc.ngay_thi
                ):
                    raise ValueError(
                        "Lịch thi lại phải sau ngày thi trước."
                    )

                da_trung = (
                    LichThi.objects
                    .filter(
                        ma_nv=nv_khoa,
                        ngay_thi=ngay_thi,
                        ca_thi=CA_THI[ca_thi]
                    )
                    .exclude(
                        ma_lt__startswith="BANKLT"
                    )
                    .exists()
                )

                if da_trung:
                    raise ValueError(
                        "Nhân viên đã có lịch thi "
                        "trùng ngày và ca."
                    )

                lich_moi = LichThi.objects.create(
                    ma_lt="LT" + uuid.uuid4().hex[:16],
                    ma_nv=nv_khoa,
                    ngay_thi=ngay_thi,
                    ca_thi=CA_THI[ca_thi]
                )

                # Giữ nguyên hàm tạo đề hiện tại.
                de_moi = tao_de_random(
                    lich_thi=lich_moi,
                    vi_tri=nv_khoa.vi_tri,
                    so_cau=10
                )

                if not CauHoi.objects.filter(
                    ma_dt=de_moi
                ).exists():
                    raise ValueError(
                        "Không tạo được câu hỏi cho đề thi."
                    )

        except ValueError as error:
            messages.error(
                request,
                str(error)
            )
            return redirect(
                "training:bo_tri_thi",
                ma_nv=ma_nv
            )

        messages.success(
            request,
            f"Đã bố trí lịch thi cho "
            f"{nhan_vien.ho_ten} thành công!"
        )

        return redirect(
            "training:dashboard_quan_ly_tap_su"
        )

    # ===============================
    # HIỂN THỊ FORM
    # ===============================

    context = {
        "active_menu": "training",
        "nhan_vien": nhan_vien,
        "chuong_trinh": chuong_trinh,
        "tong_bai": tong_bai,
        "so_bai_dat": so_bai_dat,
        "phan_tram": phan_tram,
        "ngay_hoan_thanh": ngay_hoan_thanh,
        "ds_de_thi": ds_de_thi,
        "lich_thi_da_co": lich_thi_da_co,
        "ca_thi_choices": CA_THI,
        "ngay_hom_nay": timezone.localdate(),
        "la_thi_lai": thong_tin["la_thi_lai"],
    }

    return render(
        request,
        "training/bo_tri_thi.html",
        context
    )

@login_required
def dao_tao(request):

    if (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    ):
        return redirect(
            'training:dashboard_quan_ly_tap_su'
        )

    elif getattr(request.user, 'role', None) == 'employee':
        return redirect(
            'training:dao_tao_nhan_vien'
        )

    raise PermissionDenied(
        'Bạn không có quyền truy cập phân hệ Đào tạo.'
    )

@login_required
def dao_tao_nhan_vien(request):

    # Chỉ nhân viên được truy cập
    if request.user.role != 'employee':
        raise PermissionDenied

    # 1. Xác định hồ sơ của người đang đăng nhập
    nhan_vien = NhanVien.objects.filter(
        tai_khoan=request.user
    ).first()

    chuong_trinh = None
    cac_buoi = []
    tong_bai = 0
    so_bai_dat = 0
    tien_do = 0

    if nhan_vien:

        # 2. Lấy chương trình đã được phê duyệt
        # của chính nhân viên đó
        chuong_trinh = (
            ChuongTrinhTapSu.objects
            .select_related('ma_khung', 'ma_nv')
            .filter(
                ma_nv=nhan_vien,
                trang_thai_duyet='Đã duyệt'
            )
            .order_by('-ma_ct')
            .first()
        )

        if chuong_trinh:

            # 3. Lấy bài học thật từ database
            ds_bai_hoc = list(
                BaiHoc.objects.filter(
                    ma_ct=chuong_trinh
                ).order_by(
                    'buoi_hoc',
                    'ma_bh'
                )
            )

            # 4. Lấy kết quả đánh giá từng bài
            # Chỉ lấy của nhân viên này
            ds_tien_do = (
                TienDoTapSu.objects
                .filter(
                    ma_nv=nhan_vien,
                    ma_bh__in=ds_bai_hoc
                )
                .order_by('ngay_danh_gia', 'ma_td')
            )

            tien_do_theo_bai = {}

            for td in ds_tien_do:
                tien_do_theo_bai[td.ma_bh_id] = td

            # 5. Gom bài học theo từng buổi
            nhom_buoi = {}

            for bai in ds_bai_hoc:

                so_buoi = bai.buoi_hoc or 0

                if so_buoi not in nhom_buoi:
                    nhom_buoi[so_buoi] = {
                        'so': so_buoi,
                        'bai_hoc': [],
                        'so_bai': 0,
                        'so_bai_dat': 0,
                        'trang_thai': 'chua_hoc',
                    }

                buoi = nhom_buoi[so_buoi]

                # Lấy kết quả của bài hiện tại
                td = tien_do_theo_bai.get(bai.ma_bh)

                trang_thai = 'chua_hoc'
                ten_trang_thai = 'Chưa học'
                ngay_danh_gia = None

                if td:
                    gia_tri = (
                        td.trang_thai_danh_gia or ''
                    ).strip().lower()

                    ngay_danh_gia = td.ngay_danh_gia

                    if gia_tri == 'đạt':
                        trang_thai = 'dat'
                        ten_trang_thai = 'Đạt'

                    elif gia_tri in (
                        'chưa đạt',
                        'không đạt'
                    ):
                        trang_thai = 'chua_dat'
                        ten_trang_thai = 'Chưa đạt'

                # Đưa bài học vào đúng buổi
                buoi['bai_hoc'].append({
                    'ma_bh': bai.ma_bh,
                    'ten': bai.ten_bh,
                    'loai': bai.loai_bh,
                    'thoi_luong': bai.thoi_gian_hoc,
                    'trang_thai': trang_thai,
                    'ten_trang_thai': ten_trang_thai,
                    'ngay': ngay_danh_gia,
                })

                buoi['so_bai'] += 1
                tong_bai += 1

                if trang_thai == 'dat':
                    buoi['so_bai_dat'] += 1
                    so_bai_dat += 1

            # 6. Tính trạng thái từng buổi
            for buoi in nhom_buoi.values():

                if (
                    buoi['so_bai'] > 0
                    and buoi['so_bai_dat'] == buoi['so_bai']
                ):
                    buoi['trang_thai'] = 'hoan_thanh'

                elif any(
                    bai['trang_thai'] != 'chua_hoc'
                    for bai in buoi['bai_hoc']
                ):
                    buoi['trang_thai'] = 'dang_hoc'

                else:
                    buoi['trang_thai'] = 'chua_hoc'

                # Gom các loại hình thức trong buổi
                cac_loai = list(dict.fromkeys(
                    bai['loai']
                    for bai in buoi['bai_hoc']
                    if bai['loai']
                ))

                buoi['loai_hoc'] = ', '.join(cac_loai)

            cac_buoi = list(nhom_buoi.values())

            # 7. Tính tỷ lệ hoàn thành
            if tong_bai > 0:
                tien_do = round(
                    so_bai_dat * 100 / tong_bai,
                    1
                )

    # 8. Truyền dữ liệu sang giao diện
    context = {
        'active_menu': 'training',
        'nhan_vien': nhan_vien,
        'chuong_trinh': chuong_trinh,
        'cac_buoi': cac_buoi,
        'so_buoi': len(cac_buoi),
        'tong_bai': tong_bai,
        'so_bai_dat': so_bai_dat,
        'tien_do': tien_do,
    }

    return render(
        request,
        'training/dao_tao_nhan_vien.html',
        context
    )

@login_required
def chinh_sua_chuong_trinh(request, pk):

    # Chỉ quản lý được chỉnh sửa

    if not (
            request.user.is_superuser
            or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied(
            'Chỉ quản lý được chỉnh sửa chương trình đào tạo.'
        )

    # Lấy chương trình theo mã từ database
    chuong_trinh = get_object_or_404(
        ChuongTrinhTapSu.objects.select_related(
            'ma_nv',
            'ma_khung'
        ),
        pk=pk
    )

    # Không cho chỉnh chương trình đã duyệt
    if chuong_trinh.trang_thai_duyet == 'Đã duyệt':
        messages.error(
            request,
            'Chương trình đã phê duyệt không thể '
            'chỉnh sửa tại đây.'
        )
        return redirect(
            'training:duyet_chuong_trinh',
            pk=pk
        )

    # ======================================
    # XỬ LÝ KHI NHẤN LƯU CHỈNH SỬA
    # ======================================
    if request.method == 'POST':
        print("DEBUG POST:", request.POST.dict())
        ma_bh_list = request.POST.getlist('ma_bh[]')
        ten_list = request.POST.getlist('ten_bh[]')
        buoi_list = request.POST.getlist('buoi_hoc[]')
        loai_list = request.POST.getlist('loai_bh[]')
        phut_list = request.POST.getlist('thoi_gian_hoc[]')

        count = len(ten_list)

        # Kiểm tra số lượng dữ liệu nhận được
        if (
            count < 1
            or count > 100
            or any(
                len(ds) != count
                for ds in (
                    ma_bh_list,
                    buoi_list,
                    loai_list,
                    phut_list,
                )
            )
        ):
            messages.error(
                request,
                'Danh sách bài học không hợp lệ.'
            )
            return redirect(
                'training:chinh_sua_chuong_trinh',
                pk=pk
            )

        # Các hình thức đào tạo được cho phép
        loai_hop_le = {
            'Thực hành OJT',
            'Lý thuyết & OJT',
        }

        du_lieu_sach = []

        # ======================================
        # KIỂM TRA DỮ LIỆU TỪ FORM
        # ======================================
        try:
            for i in range(count):

                ma_bh = ma_bh_list[i].strip()
                ten_bh = ten_list[i].strip()
                buoi_hoc = int(buoi_list[i])
                loai_bh = loai_list[i].strip()
                thoi_gian_hoc = int(phut_list[i])

                if not ten_bh or len(ten_bh) > 255:
                    raise ValueError(
                        'Tên bài học không hợp lệ.'
                    )

                if not 1 <= buoi_hoc <= 999:
                    raise ValueError(
                        'Số buổi học không hợp lệ.'
                    )

                if not 1 <= thoi_gian_hoc <= 1440:
                    raise ValueError(
                        'Thời lượng phải từ 1 đến 1440 phút.'
                    )

                if loai_bh not in loai_hop_le:
                    raise ValueError(
                        'Hình thức đào tạo không hợp lệ.'
                    )

                du_lieu_sach.append({
                    'ma_bh': ma_bh,
                    'ten_bh': ten_bh,
                    'buoi_hoc': buoi_hoc,
                    'loai_bh': loai_bh,
                    'thoi_gian_hoc': thoi_gian_hoc,
                })

        except (ValueError, TypeError) as error:
            messages.error(request, str(error))
            return redirect(
                'training:chinh_sua_chuong_trinh',
                pk=pk
            )

        # Kiểm tra bài học bị gửi trùng mã
        ids = [
            item['ma_bh']
            for item in du_lieu_sach
            if item['ma_bh']
        ]

        if len(ids) != len(set(ids)):
            messages.error(
                request,
                'Có bài học bị gửi trùng mã.'
            )
            return redirect(
                'training:chinh_sua_chuong_trinh',
                pk=pk
            )

        # ======================================
        # LƯU THAY ĐỔI VÀO DATABASE
        # ======================================
        with transaction.atomic():

            # Khóa chương trình khi lưu
            ct = (
                ChuongTrinhTapSu.objects
                .select_for_update()
                .get(pk=pk)
            )

            if ct.trang_thai_duyet == 'Đã duyệt':
                messages.error(
                    request,
                    'Chương trình vừa được phê duyệt. '
                    'Không thể tiếp tục chỉnh sửa.'
                )
                return redirect(
                    'training:duyet_chuong_trinh',
                    pk=pk
                )

            # Các bài học hiện tại của chương trình
            bai_hoc_cu = {
                bai.pk: bai
                for bai in (
                    BaiHoc.objects
                    .select_for_update()
                    .filter(ma_ct=ct)
                )
            }

            # Không được sửa bài học của chương trình khác
            if any(
                ma not in bai_hoc_cu
                for ma in ids
            ):
                messages.error(
                    request,
                    'Có bài học không thuộc chương trình này.'
                )
                return redirect(
                    'training:chinh_sua_chuong_trinh',
                    pk=pk
                )

            # Xác định các bài đã bị xóa trên giao diện
            ids_xoa = set(bai_hoc_cu) - set(ids)

            # Không xóa bài học đã có kết quả đánh giá
            da_co_danh_gia = (
                TienDoTapSu.objects.filter(
                    ma_bh_id__in=ids_xoa
                ).exists()
            )

            if da_co_danh_gia:
                messages.error(
                    request,
                    'Không thể xóa bài học đã có '
                    'kết quả đánh giá OJT.'
                )
                return redirect(
                    'training:chinh_sua_chuong_trinh',
                    pk=pk
                )

            # Xóa các bài không còn trong form
            BaiHoc.objects.filter(
                ma_ct=ct,
                pk__in=ids_xoa
            ).delete()

            # Cập nhật bài cũ hoặc thêm bài mới
            for item in du_lieu_sach:
                ma_bh = item['ma_bh']

                if ma_bh:
                    # Bài học đã tồn tại
                    bai = bai_hoc_cu[ma_bh]

                    bai.ten_bh = item['ten_bh']
                    bai.buoi_hoc = item['buoi_hoc']
                    bai.loai_bh = item['loai_bh']
                    bai.thoi_gian_hoc = item['thoi_gian_hoc']

                    bai.save(update_fields=[
                        'ten_bh',
                        'buoi_hoc',
                        'loai_bh',
                        'thoi_gian_hoc',
                    ])

                else:
                    # Bài học mới được thêm
                    BaiHoc.objects.create(
                        ma_bh='BH' + uuid.uuid4().hex[:16],
                        ma_ct=ct,
                        ten_bh=item['ten_bh'],
                        buoi_hoc=item['buoi_hoc'],
                        loai_bh=item['loai_bh'],
                        thoi_gian_hoc=item['thoi_gian_hoc'],
                    )

        messages.success(
            request,
            'Đã lưu chỉnh sửa chương trình tập sự.'
        )

        return redirect(
            'training:duyet_chuong_trinh',
            pk=pk
        )

    # ======================================
    # GET: HIỂN THỊ TRANG CHỈNH SỬA
    # ======================================

    # Các bài học thực tế của nhân viên
    ds_bai_hoc = BaiHoc.objects.filter(
        ma_ct=chuong_trinh
    ).order_by(
        'buoi_hoc',
        'ma_bh'
    )

    # Danh mục bài học mặc định thuộc khung đào tạo
    bai_hoc_mau = BaiHocKhungMau.objects.filter(
        ma_khung=chuong_trinh.ma_khung
    ).order_by(
        'buoi_hoc',
        'ma_bhk'
    )

    context = {
        'active_menu': 'training',
        'chuong_trinh': chuong_trinh,
        'ds_bai_hoc': ds_bai_hoc,
        'bai_hoc_mau': bai_hoc_mau,
    }

    return render(
        request,
        'training/chinh_sua_chuong_trinh.html',
        context
    )


@login_required
def lich_thi_nhan_vien(request):

    # 1. Chỉ nhân viên được truy cập
    if request.user.role != 'employee':
        raise PermissionDenied

    # 2. Xác định hồ sơ của tài khoản đang đăng nhập
    nhan_vien = NhanVien.objects.filter(
        tai_khoan=request.user
    ).first()

    chuong_trinh = None
    lich_thi = None
    de_thi = None
    tong_cau_hoi = 0
    tong_bai = 0
    so_bai_dat = 0
    tien_do = 0
    ngay_hoan_thanh = None

    ngay_hom_nay = timezone.localdate()

    if nhan_vien:

        # 3. Lấy chương trình đã duyệt của nhân viên
        chuong_trinh = (
            ChuongTrinhTapSu.objects
            .select_related('ma_khung')
            .filter(
                ma_nv=nhan_vien,
                trang_thai_duyet='Đã duyệt'
            )
            .order_by('-ma_ct')
            .first()
        )

        if chuong_trinh:

            # 4. Lấy bài học của chương trình
            ds_bai_hoc = list(
                BaiHoc.objects.filter(
                    ma_ct=chuong_trinh
                ).order_by('buoi_hoc', 'ma_bh')
            )

            tong_bai = len(ds_bai_hoc)

            # 5. Lấy các kết quả OJT đã lưu
            danh_gia = (
                TienDoTapSu.objects
                .filter(
                    ma_nv=nhan_vien,
                    ma_bh__in=ds_bai_hoc
                )
                .order_by('ngay_danh_gia', 'ma_td')
            )

            danh_gia_theo_bai = {}

            for item in danh_gia:
                danh_gia_theo_bai[item.ma_bh_id] = item

            # 6. Tính số bài đạt thực tế
            ngay_dat = []

            for bai in ds_bai_hoc:

                ket_qua = danh_gia_theo_bai.get(
                    bai.ma_bh
                )

                if ket_qua is None:
                    continue

                trang_thai = (
                    ket_qua.trang_thai_danh_gia or ''
                ).strip().lower()

                if trang_thai == 'đạt':
                    so_bai_dat += 1

                    if ket_qua.ngay_danh_gia:
                        ngay_dat.append(
                            ket_qua.ngay_danh_gia
                        )

            if tong_bai > 0:
                tien_do = round(
                    so_bai_dat * 100 / tong_bai,
                    1
                )

            # 7. Chỉ xác định ngày hoàn thành
            # khi đã đạt tất cả bài học
            if tong_bai > 0 and so_bai_dat == tong_bai:
                if ngay_dat:
                    ngay_hoan_thanh = max(ngay_dat)

                # 8. Lấy lịch thi đã đăng ký
                # cho chính nhân viên đăng nhập

                # Lấy các lịch thi thật của nhân viên
                ds_lich_thi = (
                    LichThi.objects
                    .filter(ma_nv=nhan_vien)
                    .exclude(ma_lt__startswith='BANKLT')
                    .order_by('-ngay_thi', '-ma_lt')
                )

                lich_thi = None

                # Ưu tiên lịch thi chưa có kết quả
                for lich in ds_lich_thi:

                    da_nop = KetQuaThi.objects.filter(
                        ma_lt=lich
                    ).exists()

                    if not da_nop:
                        lich_thi = lich
                        break

                # Nếu đã thi tất cả lịch, hiển thị lịch gần nhất
                if lich_thi is None:
                    lich_thi = ds_lich_thi.first()

                if lich_thi:
                    # 9. Lấy đề thi gắn với lịch thi
                    de_thi = (
                        DeThi.objects
                        .filter(ma_lt=lich_thi)
                        .order_by('ma_dt')
                        .first()
                    )

                    if de_thi:
                        tong_cau_hoi = (
                            de_thi.cauhoi_set.count()
                        )

    # 10. Trạng thái thời gian của lịch thi

    # Các ca thi đang sử dụng trong hệ thống
    GIO_CA_THI = {
        'Ca Sáng (09:00 - 10:00)': (9, 0, 10, 0),
        'Ca Chiều (12:00 - 15:00)': (12, 0, 15, 0),
        'Ca Tối (19:00 - 20:00)': (19, 0, 20, 0),
    }

    trang_thai_lich = 'chua_co_lich'
    duoc_bat_dau = False

    if lich_thi:

        ca = GIO_CA_THI.get(lich_thi.ca_thi)

        if ca is None:
            trang_thai_lich = 'ca_khong_hop_le'

        else:
            gio_bd, phut_bd, gio_kt, phut_kt = ca

            bat_dau = timezone.make_aware(
                datetime.combine(
                    lich_thi.ngay_thi,
                    time(gio_bd, phut_bd)
                ),
                timezone.get_current_timezone()
            )

            ket_thuc = timezone.make_aware(
                datetime.combine(
                    lich_thi.ngay_thi,
                    time(gio_kt, phut_kt)
                ),
                timezone.get_current_timezone()
            )

            hien_tai = timezone.now()

            if hien_tai < bat_dau:
                trang_thai_lich = 'chua_den_gio'

            elif hien_tai >= ket_thuc:
                trang_thai_lich = 'het_ca_thi'

            elif de_thi is None:
                trang_thai_lich = 'chua_co_de'

            else:
                trang_thai_lich = 'duoc_lam_bai'
                duoc_bat_dau = True

    trang_thai_lich, duoc_bat_dau = (
        xac_dinh_trang_thai_thi(
            lich_thi,
            de_thi
        )
    )

    context = {
        'active_menu': 'training',
        'nhan_vien': nhan_vien,
        'chuong_trinh': chuong_trinh,
        'lich_thi': lich_thi,
        'de_thi': de_thi,
        'tong_cau_hoi': tong_cau_hoi,
        'tong_bai': tong_bai,
        'so_bai_dat': so_bai_dat,
        'tien_do': tien_do,
        'ngay_hoan_thanh': ngay_hoan_thanh,
        # Trạng thái mở đề thi tự động
        'trang_thai_lich': trang_thai_lich,
        'duoc_bat_dau': duoc_bat_dau,
        'trang_thai_lich': trang_thai_lich,
        'duoc_bat_dau': duoc_bat_dau,
    }
    return render(
        request,
        'training/lich_thi_nhan_vien.html',
        context
    )