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

# ----------------------------------------------------
# 1. HÀM HIỂN THỊ MAIN DASHBOARD & BỘ LỌC
# ----------------------------------------------------
GIO_CA_THI = {
    'Sang': (9, 0, 10, 0),
    'Chieu': (14, 0, 15, 0),
    'Toi': (19, 0, 20, 0),

    # Hỗ trợ dữ liệu cũ đã lưu tên đầy đủ
    'Ca Sáng (09:00 - 10:00)': (9, 0, 10, 0),
    'Ca Chiều (14:00 - 15:00)': (14, 0, 15, 0),
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
    # 1.1 Tính toán chỉ số cho 4 thẻ Thống kê (Metric Cards)
    tong_so_tap_su = NhanVien.objects.filter(trang_thai='Tap_su').count()
    cho_duyet_lo_trinh = ChuongTrinhTapSu.objects.filter(trang_thai_duyet='Chờ duyệt').count()
    dang_thuc_hanh_ojt = ChuongTrinhTapSu.objects.filter(trang_thai_duyet='Đã duyệt', tong_tien_do__lt=100).count()
    du_dieu_kien_thi = ChuongTrinhTapSu.objects.filter(tong_tien_do=100).count()

    # 1.2 Xử lý Lọc & Tìm kiếm
    search_query = request.GET.get('search', '')
    vi_tri = request.GET.get('vi_tri', '')
    hinh_thuc = request.GET.get('hinh_thuc', '')
    trang_thai_filter = request.GET.get('trang_thai', '')

    chuong_trinh_qs = ChuongTrinhTapSu.objects.select_related('ma_nv').all()

    if request.user.role != 'admin':
        raise PermissionDenied

    if search_query:
        chuong_trinh_qs = chuong_trinh_qs.filter(
            Q(ma_nv__ho_ten__icontains=search_query) | Q(ma_nv__ma_nv__icontains=search_query)
        )
    if vi_tri:
        chuong_trinh_qs = chuong_trinh_qs.filter(ma_nv__vitri=vi_tri)
    if hinh_thuc:
        chuong_trinh_qs = chuong_trinh_qs.filter(ma_nv__hinh_thuc=hinh_thuc)
    if trang_thai_filter:
        chuong_trinh_qs = chuong_trinh_qs.filter(trang_thai_duyet=trang_thai_filter)

    context = {
        'active_menu': 'training',  # Active thanh menu bên trái
        'tong_so_tap_su': tong_so_tap_su,
        'cho_duyet_lo_trinh': cho_duyet_lo_trinh,
        'dang_thuc_hanh_ojt': dang_thuc_hanh_ojt,
        'du_dieu_kien_thi': du_dieu_kien_thi,
        'danh_sach_tap_su': chuong_trinh_qs,
    }
    return render(request, 'training/dashboard.html', context)

@login_required
def tao_ho_so_tap_su(request):

    # Chỉ quản lý được tạo hồ sơ tập sự
    if request.user.role != 'admin':
        raise PermissionDenied

    # Lấy các khung đào tạo từ database
    ds_khung = KhungChuongTrinh.objects.all().order_by('vi_tri')

    if request.method == 'POST':

        # 1. Lấy thông tin từ form
        ho_ten = request.POST.get('ho_ten', '').strip()
        ngay_sinh = request.POST.get('ngay_sinh') or None
        sdt = request.POST.get('sdt', '').strip()
        email = request.POST.get('email', '').strip()
        gioi_tinh = request.POST.get('gioi_tinh', 'Nữ')
        dia_chi = request.POST.get('dia_chi', '').strip()
        vi_tri = request.POST.get('vi_tri', '').strip()

        # 2. Kiểm tra thông tin
        if not ho_ten or not vi_tri:
            messages.error(
                request,
                'Vui lòng nhập họ tên và vị trí làm việc.'
            )
            return redirect('training:tao_ho_so_tap_su')

        # 3. Tìm khung đào tạo tương ứng với vị trí
        khung = KhungChuongTrinh.objects.filter(
            vi_tri__iexact=vi_tri
        ).first()

        if khung is None:
            messages.error(
                request,
                f'Chưa có khung đào tạo cho vị trí {vi_tri}.'
            )
            return redirect('training:tao_ho_so_tap_su')

        # 4. Lấy bài học từ khung mẫu trong database
        bai_hoc_mau = list(
            BaiHocKhungMau.objects.filter(
                ma_khung=khung
            ).order_by('buoi_hoc', 'ma_bhk')
        )

        if not bai_hoc_mau:
            messages.error(
                request,
                'Khung đào tạo này chưa có bài học mẫu.'
            )
            return redirect('training:tao_ho_so_tap_su')

        # 5. Tạo hồ sơ, chương trình và bài học cùng lúc
        with transaction.atomic():

            # Tìm mã nhân viên tiếp theo chưa được sử dụng
            cac_ma_nv = NhanVien.objects.values_list(
                'manv', flat=True
            )

            so_lon_nhat = 0

            for ma in cac_ma_nv:
                ket_qua = re.fullmatch(
                    r'NV(\d+)', ma or ''
                )

                if ket_qua:
                    so_lon_nhat = max(
                        so_lon_nhat,
                        int(ket_qua.group(1))
                    )

            ma_nv_moi = f'NV{so_lon_nhat + 1:03d}'

            # Tạo nhân viên
            nv = NhanVien.objects.create(
                manv=ma_nv_moi,
                ho_ten=ho_ten,
                ngay_sinh=ngay_sinh,
                sdt=sdt,
                email=email,
                gioi_tinh=gioi_tinh,
                dia_chi=dia_chi,
                vi_tri=vi_tri,
                trang_thai='Tap_su'
            )

            # Tạo chương trình tập sự
            ma_ct_moi = 'CT' + uuid.uuid4().hex[:16]

            chuong_trinh = ChuongTrinhTapSu.objects.create(
                ma_ct=ma_ct_moi,
                ma_nv=nv,
                ma_khung=khung,
                ten_ct=khung.ten_khung,
                trang_thai_duyet='Chờ duyệt',
                tong_tien_do=0
            )

            # Sao chép bài học từ khung mẫu
            ds_bai_hoc_moi = []

            for bai_mau in bai_hoc_mau:

                # "Buổi 1" -> 1, "Buổi 2" -> 2
                ket_qua = re.search(
                    r'\d+', bai_mau.buoi_hoc or ''
                )

                so_buoi = (
                    int(ket_qua.group())
                    if ket_qua else None
                )

                ds_bai_hoc_moi.append(
                    BaiHoc(
                        ma_bh='BH' + uuid.uuid4().hex[:16],
                        ma_ct=chuong_trinh,
                        ten_bh=bai_mau.ten_bai_hoc,
                        loai_bh=bai_mau.hinh_thuc,
                        buoi_hoc=so_buoi,
                        thoi_gian_hoc=bai_mau.thoi_luong
                    )
                )

            BaiHoc.objects.bulk_create(
                ds_bai_hoc_moi
            )

        messages.success(
            request,
            f'Đã lưu hồ sơ {nv.ho_ten} ({nv.manv}). '
            'Vui lòng kiểm tra và phê duyệt chương trình.'
        )

        # 6. Chuyển thẳng đến trang duyệt chương trình
        return redirect(
            'training:duyet_chuong_trinh',
            pk=chuong_trinh.pk
        )

    # GET: Hiển thị form tạo hồ sơ
    cac_ma_nv = NhanVien.objects.values_list(
        'manv', flat=True
    )

    so_lon_nhat = 0

    for ma in cac_ma_nv:
        ket_qua = re.fullmatch(r'NV(\d+)', ma or '')
        if ket_qua:
            so_lon_nhat = max(
                so_lon_nhat, int(ket_qua.group(1))
            )

    context = {
        'ma_nv_du_kien': f'NV{so_lon_nhat + 1:03d}',
        'ds_khung': ds_khung,
        'active_menu': 'training',
    }

    return render(
        request,
        'training/tao_ho_so.html',
        context
    )


# ----------------------------------------------------
# 2. HÀM HIỂN THỊ LỘ TRÌNH ĐÀO TẠO OJT
# ----------------------------------------------------
def lo_trinh_tap_su(request, ma_ct):
    chuong_trinh = get_object_or_404(ChuongTrinhTapSu, pk=ma_ct)
    ds_tien_do = TienDoTapSu.objects.filter(ma_ct=chuong_trinh).select_related('ma_bai_hoc')
    context = {
        'chuong_trinh': chuong_trinh,
        'ds_tien_do': ds_tien_do,
    }
    return render(request, 'training/lo_trinh.html', context)

# ----------------------------------------------------
# 3. HÀM HIỂN THỊ KẾT QUẢ THI
# ----------------------------------------------------
@login_required
def ket_qua_thi(request, ma_kq):
    ket_qua = get_object_or_404(KetQuaThi, pk=ma_kq)
    return render(request, 'training/ket_qua_thi.html', {'ket_qua': ket_qua})


@login_required
def duyet_chuong_trinh(request, pk):

    # Chỉ quản lý được truy cập
    if request.user.role != 'admin':
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
    chuong_trinh = get_object_or_404(ChuongTrinhTapSu, pk=ma_ct)
    chuong_trinh.trang_thai_duyet = 'Đã duyệt'
    chuong_trinh.save()
    messages.success(request, f"Đã duyệt lộ trình đào tạo cho NV {chuong_trinh.ma_nv.ho_ten}!")
    return redirect('training:dashboard_quan_ly_tap_su')

# ----------------------------------------------------
# 5. HÀM THAO TÁC: TÍCH CHECKLIST TĂNG TIẾN ĐỘ OJT
# ----------------------------------------------------

@login_required
def cap_nhat_tien_do_ojt(request, ma_nv):

    # 1. Chỉ quản lý được đánh giá OJT
    if request.user.role != 'admin':
        raise PermissionDenied

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

    # Chỉ quản lý được bố trí thi
    if request.user.role != 'admin':
        raise PermissionDenied

    # Các ca thi mà cửa hàng tổ chức
    CA_THI = {
        'Sang': 'Ca Sáng (09:00 - 10:00)',
        'Chieu': 'Ca Chiều (14:00 - 15:00)',
        'Toi': 'Ca Tối (19:00 - 20:00)',
    }

    # 1. Lấy chương trình đã duyệt của nhân viên
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
        messages.error(
            request,
            'Nhân viên chưa có chương trình được duyệt.'
        )
        return redirect(
            'training:dashboard_quan_ly_tap_su'
        )

    nhan_vien = chuong_trinh.ma_nv

    # 2. Tính lại tiến độ bằng kết quả đánh giá thật
    ds_bai_hoc = list(
        BaiHoc.objects.filter(
            ma_ct=chuong_trinh
        ).order_by('buoi_hoc', 'ma_bh')
    )

    tong_bai = len(ds_bai_hoc)

    tien_do_theo_bai = {}

    ds_danh_gia = (
        TienDoTapSu.objects
        .filter(
            ma_nv=nhan_vien,
            ma_bh__in=ds_bai_hoc
        )
        .order_by('ngay_danh_gia', 'ma_td')
    )

    for danh_gia in ds_danh_gia:
        tien_do_theo_bai[danh_gia.ma_bh_id] = danh_gia

    so_bai_dat = sum(
        1
        for bai in ds_bai_hoc
        if (
            bai.ma_bh in tien_do_theo_bai
            and (
                tien_do_theo_bai[bai.ma_bh]
                .trang_thai_danh_gia or ''
            ).strip().lower() == 'đạt'
        )
    )

    phan_tram = (
        round(so_bai_dat * 100 / tong_bai, 1)
        if tong_bai else 0
    )

    # Chưa hoàn thành 100% thì không được bố trí thi
    if tong_bai == 0 or so_bai_dat != tong_bai:
        messages.error(
            request,
            'Nhân viên chưa hoàn thành 100% bài học OJT.'
        )
        return redirect(
            'training:dashboard_quan_ly_tap_su'
        )

    # Ngày hoàn thành OJT:
    # lấy ngày đánh giá muộn nhất của các bài đã đạt
    ngay_hoan_thanh = max(
        (
            danh_gia.ngay_danh_gia
            for danh_gia in tien_do_theo_bai.values()
            if danh_gia.ngay_danh_gia is not None
        ),
        default=None
    )

    # 3. Các đề thi đã có câu hỏi trong database
    # được dùng làm nguồn để tạo đề cho lịch mới
    ds_de_thi = (
        DeThi.objects
        .filter(cauhoi__isnull=False)
        .distinct()
        .order_by('ten_de_thi', 'ma_dt')
    )

    # 4. Những lịch thi đã đăng ký của nhân viên
    lich_thi_da_co = (LichThi.objects.filter(ma_nv=nhan_vien).exclude(ma_lt__startswith='BANKLT').order_by('-ngay_thi', '-ma_lt'))

    # =========================================
    # XỬ LÝ KHI QUẢN LÝ XÁC NHẬN LỊCH
    # =========================================

    if request.method == 'POST':

        ngay_thi_text = request.POST.get(
            'ngay_thi', ''
        ).strip()

        ca_thi = request.POST.get(
            'ca_thi', ''
        ).strip()

        ghi_chu = request.POST.get(
            'ghi_chu', ''
        ).strip()

        so_cau = 10

        # Kiểm tra ngày thi
        try:
            ngay_thi = date.fromisoformat(
                ngay_thi_text
            )
        except ValueError:
            messages.error(
                request,
                'Ngày thi không hợp lệ.'
            )
            return redirect(
                'training:bo_tri_thi',
                ma_nv=ma_nv
            )

        if ngay_thi < date.today():
            messages.error(
                request,
                'Không thể bố trí ngày thi trong quá khứ.'
            )
            return redirect(
                'training:bo_tri_thi',
                ma_nv=ma_nv
            )

        if ca_thi not in CA_THI:
            messages.error(
                request,
                'Vui lòng chọn ca thi hợp lệ.'
            )
            return redirect(
                'training:bo_tri_thi',
                ma_nv=ma_nv
            )

        # Kiểm tra trùng lịch thi

        da_trung = (
            LichThi.objects.filter(
                ma_nv=nhan_vien,
                ngay_thi=ngay_thi,
                ca_thi=CA_THI[ca_thi]
            )
            .exclude(ma_lt__startswith='BANKLT')
            .exists()
        )

        # 5. Lưu lịch thi, đề thi và câu hỏi
        try:
            with transaction.atomic():

                lich_moi = LichThi.objects.create(
                    ma_lt='LT' + uuid.uuid4().hex[:16],
                    ma_nv=nhan_vien,
                    ngay_thi=ngay_thi,
                    ca_thi=CA_THI[ca_thi]
                )

                de_moi = tao_de_random(
                    lich_thi=lich_moi,
                    vi_tri=nhan_vien.vi_tri,
                    so_cau=10
                )

        except ValueError as e:
            messages.error(request, str(e))
            return redirect(
                'training:bo_tri_thi',
                ma_nv=ma_nv
            )

            # Sao chép câu hỏi sang đề vừa được gán
            for cau_hoi in ds_cau_hoi:

                CauHoi.objects.create(
                    ma_ch='CH' + uuid.uuid4().hex[:16],
                    ma_dt=de_moi,
                    noi_dung_ch=cau_hoi.noi_dung_ch,
                    dap_an_dung=cau_hoi.dap_an_dung,
                    diem=cau_hoi.diem
                )

        messages.success(
            request,
            f'Đã bố trí lịch thi tổng kết cho '
            f'{nhan_vien.ho_ten} thành công!'
        )

        return redirect(
            'training:bo_tri_thi',
            ma_nv=ma_nv
        )

    # =========================================
    # HIỂN THỊ GIAO DIỆN
    # =========================================
    context = {
        'active_menu': 'training',
        'nhan_vien': nhan_vien,
        'chuong_trinh': chuong_trinh,
        'tong_bai': tong_bai,
        'so_bai_dat': so_bai_dat,
        'phan_tram': phan_tram,
        'ngay_hoan_thanh': ngay_hoan_thanh,
        'ds_de_thi': ds_de_thi,
        'lich_thi_da_co': lich_thi_da_co,
        'ca_thi_choices': CA_THI,
        'ngay_hom_nay': date.today(),
    }

    return render(
        request,
        'training/bo_tri_thi.html',
        context
    )

@login_required
def dao_tao(request):
    if request.user.role == 'admin':
        return redirect('training:dashboard_quan_ly_tap_su')

    elif request.user.role == 'employee':
        return redirect('training:dao_tao_nhan_vien')

    raise PermissionDenied



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
    if request.user.role != 'admin':
        raise PermissionDenied

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
        'Ca Chiều (14:00 - 15:00)': (14, 0, 15, 0),
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