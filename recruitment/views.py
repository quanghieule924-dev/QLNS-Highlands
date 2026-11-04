from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DotTuyenDung, ViTriTuyenDung, UngVien, HoSoUngTuyen
from django.core.paginator import Paginator
from django.db.models import Q


@login_required
def quan_ly_tuyen_dung(request):
    if request.method == 'POST':
        ma_dot = request.POST.get('ma_dot')
        if not ma_dot:
            count_dot = DotTuyenDung.objects.count() + 1
            ma_dot = f"DT{count_dot:03d}"

        ten_dot = request.POST.get('ten_dot')
        vi_tri_str = request.POST.get('ma_vi_tri')
        so_luong = request.POST.get('so_luong_can_tuyen')
        muc_luong = request.POST.get('muc_luong')
        ngay_bat_dau_str = request.POST.get('ngay_bat_dau')
        ngay_ket_thuc_str = request.POST.get('ngay_ket_thuc')

        try:
            vi_tri_obj, created = ViTriTuyenDung.objects.get_or_create(ten_vi_tri=vi_tri_str)

            from datetime import datetime
            ngay_bd = datetime.strptime(ngay_bat_dau_str, '%Y-%m-%d').date() if ngay_bat_dau_str else None
            ngay_kt = datetime.strptime(ngay_ket_thuc_str, '%Y-%m-%d').date() if ngay_ket_thuc_str else None

            DotTuyenDung.objects.create(
                ma_dot=ma_dot,
                ten_dot=ten_dot,
                ma_vi_tri=vi_tri_obj,
                so_luong_can_tuyen=int(so_luong) if so_luong else 1,
                muc_luong=muc_luong if muc_luong else 'Thỏa thuận',  # Sửa 'muc_luong' thành 'luong' theo đúng Model của bro
                ngay_bat_dau=ngay_bd,
                ngay_ket_thuc=ngay_kt
            )
            messages.success(request, f'Đã tạo đợt tuyển dụng {ma_dot} thành công!')
        except Exception as e:
            # IN RA MÀN HÌNH WEB LỖI THỰC TẾ ĐỂ BIẾT NÓ ĐANG KẸT Ở ĐÂU
            print(f"CRITICAL ERROR: {str(e)}")
            raise e
            messages.error(request, f'Lỗi: {e}')

        return redirect('recruitment:quan_ly_tuyen_dung')

    hom_nay = date.today()
    danh_sach_db = DotTuyenDung.objects.all().order_by('-ma_dot')

    danh_sach = []
    so_dot_dang_mo = 0

    for item in danh_sach_db:
        if item.ngay_bat_dau and item.ngay_ket_thuc:
            if hom_nay < item.ngay_bat_dau:
                item.trang_thai_dong = 'Sắp mở'
            elif item.ngay_bat_dau <= hom_nay <= item.ngay_ket_thuc:
                item.trang_thai_dong = 'Đang tuyển'
                so_dot_dang_mo += 1
            else:
                item.trang_thai_dong = 'Đã đóng'
        else:
            item.trang_thai_dong = 'Không xác định'

        item.muc_luong_hien_thi = getattr(item, 'muc_luong', None) or getattr(item, 'luong', 'Thỏa thuận')
        danh_sach.append(item)

    tong_vi_tri_dang_tuyen = DotTuyenDung.objects.filter(ngay_bat_dau__lte=hom_nay, ngay_ket_thuc__gte=hom_nay).values(
        'ma_vi_tri').distinct().count()
    tong_nhan_su_can_tuyen = sum(int(item.so_luong_can_tuyen) for item in danh_sach if
                                 item.trang_thai_dong == 'Đang tuyển' and item.so_luong_can_tuyen)

    dat_vong_cv = HoSoUngTuyen.objects.filter(
        trang_thai__in=['Đạt vòng CV', 'Đã lên lịch', 'Chờ xác nhận', 'Đã phỏng vấn', 'Đạt phỏng vấn', 'Đã nhận việc']
    ).count()

    khong_dat_vong_cv = HoSoUngTuyen.objects.filter(
        trang_thai__in=['Không đạt vòng CV', 'Không đạt']
    ).count()

    lich_phong_van_sap_toi = HoSoUngTuyen.objects.filter(trang_thai='Đã lên lịch').count()
    ket_qua_tuyen_dung = HoSoUngTuyen.objects.filter(trang_thai__in=['Đạt', 'Không đạt']).count()

    context = {
        'danh_sach': danh_sach,
        'so_dot_dang_mo': so_dot_dang_mo,
        'tong_vi_tri_dang_tuyen': tong_vi_tri_dang_tuyen,
        'tong_nhan_su_can_tuyen': tong_nhan_su_can_tuyen,
        'dat_vong_cv': dat_vong_cv,
        'khong_dat_vong_cv': khong_dat_vong_cv,
        'lich_phong_van_sap_toi': lich_phong_van_sap_toi,
        'ket_qua_tuyen_dung': ket_qua_tuyen_dung,
        'active_menu': 'tuyen_dung',
        'sub_menu': 'tong_quan'
    }

    # NƠI TRẢ VỀ GIAO DIỆN CHUẨN KHI TRUY CẬP BẰNG PHƯƠNG THỨC GET
    return render(request, 'recruitment/noi_bo_tuyen_dung.html', context)
# 2. TRANG CÔNG KHAI DÀNH CHO ỨNG VIÊN (Có hỗ trợ tìm kiếm & lọc)
def recruitment_list_view(request):
    q = request.GET.get('q', '')
    trang_thai_filter = request.GET.get('trang_thai', '')
    muc_luong_filter = request.GET.get('muc_luong', '')
    ma_dot_filter = request.GET.get('ma_dot', '')

    danh_sach_db = DotTuyenDung.objects.all().order_by('-ma_dot')
    ngay_hom_nay = date.today()

    danh_sach_tuyen_dung = []
    tong_dang_mo = 0

    for item in danh_sach_db:
        ten_vt = "Nhân viên"
        if item.ma_vi_tri:
            if hasattr(item.ma_vi_tri, 'ten_vi_tri'):
                ten_vt = item.ma_vi_tri.ten_vi_tri
            else:
                ten_vt = str(item.ma_vi_tri)

        trang_thai = "Đang tuyển"
        if item.ngay_bat_dau and item.ngay_ket_thuc:
            if ngay_hom_nay < item.ngay_bat_dau:
                trang_thai = "Chưa mở"
            elif ngay_hom_nay > item.ngay_ket_thuc:
                trang_thai = "Đã đóng"
            else:
                trang_thai = "Đang tuyển"

        if trang_thai == "Đang tuyển":
            tong_dang_mo += 1

        ngay_bd = item.ngay_bat_dau.strftime('%d/%m/%Y') if item.ngay_bat_dau else ''
        ngay_kt = item.ngay_ket_thuc.strftime('%d/%m/%Y') if item.ngay_ket_thuc else ''
        thoi_gian_tuyen = f"{ngay_bd} - {ngay_kt}" if (ngay_bd and ngay_kt) else "Đang cập nhật"

        if q and q.lower() not in item.ten_dot.lower() and q.lower() not in ten_vt.lower():
            continue
        if trang_thai_filter and trang_thai_filter != trang_thai:
            continue
        muc_luong_val = getattr(item, 'muc_luong', 'Thỏa thuận')
        if muc_luong_filter and muc_luong_filter != muc_luong_val:
            continue
        if ma_dot_filter and ma_dot_filter.lower() not in str(item.ma_dot).lower():
            continue

        danh_sach_tuyen_dung.append({
            'ma_dot': item.ma_dot,
            'ten_dot': item.ten_dot,
            'vi_tri': ten_vt,
            'so_luong': getattr(item, 'so_luong_can_tuyen', 1),
            'muc_luong': muc_luong_val,
            'thoi_gian': thoi_gian_tuyen,
            'ngay_bat_dau': ngay_bd,
            'ngay_ket_thuc': ngay_kt,
            'trang_thai': trang_thai,
            'chi_nhanh': 'Chi nhánh Bạch Đằng, Đà Nẵng',
            'dia_chi_cn': '256 Bạch Đằng, Đà Nẵng',
        })

    paginator = Paginator(danh_sach_tuyen_dung, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'tong_dang_mo': tong_dang_mo,
        'search_query': q,
        'ma_dot_filter': ma_dot_filter,
    }
    return render(request, 'recruitment/recruitment.html', context)


# 3. CHI TIẾT ĐỢT TUYỂN DỤNG
def chi_tiet_tuyen_dung_view(request, ma_dot):
    dot_tuyen = get_object_or_404(DotTuyenDung, ma_dot=ma_dot)

    ngay_hom_nay = date.today()
    trang_thai = "Đang tuyển"
    if dot_tuyen.ngay_bat_dau and dot_tuyen.ngay_ket_thuc:
        if ngay_hom_nay < dot_tuyen.ngay_bat_dau:
            trang_thai = "Chưa mở"
        elif ngay_hom_nay > dot_tuyen.ngay_ket_thuc:
            trang_thai = "Đã đóng"

    context = {
        'dot_tuyen': dot_tuyen,
        'trang_thai': trang_thai,
    }
    return render(request, 'recruitment/chi_tiet_viec_lam.html', context)


# 4. HỒ SƠ ỨNG VIÊN (Của tôi)
def ho_so_ung_vien_view(request):
    danh_sach_db = HoSoUngTuyen.objects.select_related('ma_dot', 'ma_vi_tri', 'ma_ung_vien').all().order_by('-ngay_nop')

    danh_sach_ho_so = []
    for hs in danh_sach_db:
        danh_sach_ho_so.append({
            'ma_dot': hs.ma_dot.ma_dot if hs.ma_dot else 'DT00',
            'ten_dot': hs.ma_dot.ten_dot if hs.ma_dot else 'Đợt tuyển dụng',
            'vi_tri': hs.ma_vi_tri.ten_vi_tri if hs.ma_vi_tri else 'Nhân viên',
            'ngay_nop': hs.ngay_nop.strftime('%d/%m/%Y') if hs.ngay_nop else '',
            'trang_thai_ho_so': hs.trang_thai,
            'lich_phong_van': 'Chưa xếp lịch',
            'trang_xac_nhan_pv': 'Chưa xác nhận',
            'trang_thai_nhan_viec': 'Chờ kết quả',
        })

    context = {
        'danh_sach_ho_so': danh_sach_ho_so
    }
    return render(request, 'recruitment/ho_so_cua_toi.html', context)


# 5. XỬ LÝ NỘP HỒ SƠ
def nop_ho_so_view(request, ma_dot):
    dot_tuyen = get_object_or_404(DotTuyenDung, ma_dot=ma_dot)

    if request.method == 'POST':
        ho_ten = request.POST.get('ho_va_ten')
        ngay_sinh = request.POST.get('ngay_sinh')
        gioi_tinh = request.POST.get('gioi_tinh')
        sdt = request.POST.get('so_dien_thoai')
        email = request.POST.get('email')
        dia_chi = request.POST.get('dia_chi')
        cv_file = request.FILES.get('cv_file')

        ung_vien, created = UngVien.objects.get_or_create(
            sdt=sdt,
            defaults={
                'ma_ung_vien': f"UV{UngVien.objects.count() + 1:03d}",
                'ho_ten': ho_ten,
                'ngay_sinh': ngay_sinh if ngay_sinh else '2000-01-01',
                'email': email,
                'gioi_tinh': gioi_tinh,
                'vi_tri': dot_tuyen.ma_vi_tri.ten_vi_tri if dot_tuyen.ma_vi_tri else 'Nhân viên',
                'dia_chi': dia_chi,
                'trang_thai': 'Chờ xử lý'
            }
        )

        count_hs = HoSoUngTuyen.objects.count() + 1
        ma_hs = f"HS{count_hs:03d}"

        HoSoUngTuyen.objects.create(
            ma_ho_so=ma_hs,
            ngay_nop=date.today(),
            trang_thai='Chờ xét duyệt',
            cv_ung_vien=cv_file,
            ma_ung_vien=ung_vien,
            ma_vi_tri=dot_tuyen.ma_vi_tri,
            ma_dot=dot_tuyen
        )

        messages.success(request, 'Hồ sơ của bạn đã được nộp thành công! Chúng tôi sẽ liên hệ lại sớm nhất.')
        return redirect('recruitment:recruitment_list')

    context = {
        'dot_tuyen': dot_tuyen,
    }
    return render(request, 'recruitment/nop_ho_so.html', context)


# 6. QUẢN LÝ DANH SÁCH HỒ SƠ (HR)
@login_required
def hr_danh_sach_ho_so(request):
    danh_sach_hs = HoSoUngTuyen.objects.select_related('ma_ung_vien', 'ma_vi_tri', 'ma_dot').all().order_by('-ngay_nop')

    q = request.GET.get('q', '')
    vi_tri_filter = request.GET.get('vi_tri', '')
    ma_ho_so_filter = request.GET.get('ma_ho_so', '')
    trang_thai_filter = request.GET.get('trang_thai', '')
    ngay_nop_filter = request.GET.get('ngay_nop', '')

    if q:
        danh_sach_hs = danh_sach_hs.filter(
            Q(ma_ung_vien__ho_ten__icontains=q) |
            Q(ma_ung_vien__sdt__icontains=q) |
            Q(ma_ung_vien__email__icontains=q)
        )
    if vi_tri_filter:
        danh_sach_hs = danh_sach_hs.filter(ma_vi_tri__ten_vi_tri=vi_tri_filter)

    if ma_ho_so_filter:
        danh_sach_hs = danh_sach_hs.filter(ma_ho_so=ma_ho_so_filter)

    if trang_thai_filter:
        if trang_thai_filter == 'Đạt vòng CV':
            danh_sach_hs = danh_sach_hs.filter(
                trang_thai__in=['Đạt vòng CV', 'Đã lên lịch', 'Chờ xác nhận', 'Đã phỏng vấn', 'Đạt phỏng vấn',
                                'Đã nhận việc']
            )
        else:
            danh_sach_hs = danh_sach_hs.filter(trang_thai=trang_thai_filter)

    if ngay_nop_filter:
        danh_sach_hs = danh_sach_hs.filter(ngay_nop=ngay_nop_filter)

    if request.method == 'POST':
        ma_ho_so = request.POST.get('ma_ho_so')
        ket_qua_danh_gia = request.POST.get('ket_qua')

        if ma_ho_so and ket_qua_danh_gia:
            try:
                ho_so = HoSoUngTuyen.objects.get(ma_ho_so=ma_ho_so)
                ho_so.trang_thai = ket_qua_danh_gia
                ho_so.save()
                messages.success(request, f'Đã đánh giá hồ sơ {ma_ho_so} thành công.')
                return redirect('recruitment:hr_danh_sach_ho_so')
            except HoSoUngTuyen.DoesNotExist:
                messages.error(request, 'Không tìm thấy hồ sơ.')

    danh_sach_vi_tri = ViTriTuyenDung.objects.all()
    danh_sach_ma_hs = HoSoUngTuyen.objects.values_list('ma_ho_so', flat=True).distinct()

    context = {
        'danh_sach_hs': danh_sach_hs,
        'search_query': q,
        'vi_tri_filter': vi_tri_filter,
        'ma_ho_so_filter': ma_ho_so_filter,
        'trang_thai_filter': trang_thai_filter,
        'ngay_nop_filter': ngay_nop_filter,
        'danh_sach_vi_tri': danh_sach_vi_tri,
        'danh_sach_ma_hs': danh_sach_ma_hs,
        'active_menu': 'tuyen_dung'
    }
    return render(request, 'recruitment/hr_danh_sach_ho_so.html', context)


# 7. SÀNG LỌC CV (HR)
@login_required
def hr_sang_loc_cv(request):
    # Lấy các hồ sơ thuộc nhóm Đạt vòng CV (bao gồm cả các hồ sơ đang chuẩn bị hoặc đã lên lịch phỏng vấn)
    dat_vong_cv = HoSoUngTuyen.objects.select_related('ma_ung_vien', 'ma_vi_tri', 'ma_dot').filter(
        trang_thai__in=['Đạt vòng CV', 'Đã lên lịch', 'Chờ xác nhận', 'Đã phỏng vấn', 'Đạt phỏng vấn']
    ).order_by('-ngay_nop')

    # Lấy các hồ sơ thuộc nhóm Không đạt vòng CV
    khong_dat = HoSoUngTuyen.objects.select_related('ma_ung_vien', 'ma_vi_tri', 'ma_dot').filter(
        trang_thai='Không đạt vòng CV'
    ).order_by('-ngay_nop')

    q = request.GET.get('q', '').strip()
    vi_tri_filter = request.GET.get('vi_tri', '').strip()
    ma_ho_so_filter = request.GET.get('ma_ho_so', '').strip()
    trang_thai_filter = request.GET.get('trang_thai', '').strip()
    ngay_nop_filter = request.GET.get('ngay_nop', '').strip()

    if q:
        dat_vong_cv = dat_vong_cv.filter(
            Q(ma_ung_vien__ho_ten__icontains=q) |
            Q(ma_ung_vien__sdt__icontains=q) |
            Q(ma_ung_vien__email__icontains=q)
        )
        khong_dat = khong_dat.filter(
            Q(ma_ung_vien__ho_ten__icontains=q) |
            Q(ma_ung_vien__sdt__icontains=q) |
            Q(ma_ung_vien__email__icontains=q)
        )
    if vi_tri_filter:
        dat_vong_cv = dat_vong_cv.filter(ma_vi_tri__ten_vi_tri=vi_tri_filter)
        khong_dat = khong_dat.filter(ma_vi_tri__ten_vi_tri=vi_tri_filter)
    if ma_ho_so_filter:
        dat_vong_cv = dat_vong_cv.filter(ma_ho_so__icontains=ma_ho_so_filter)
        khong_dat = khong_dat.filter(ma_ho_so__icontains=ma_ho_so_filter)

    if trang_thai_filter:
        if trang_thai_filter == 'Đạt vòng CV':
            khong_dat = khong_dat.none()
        elif trang_thai_filter == 'Không đạt vòng CV':
            dat_vong_cv = dat_vong_cv.none()
        else:
            dat_vong_cv = dat_vong_cv.filter(trang_thai=trang_thai_filter)
            khong_dat = khong_dat.filter(trang_thai=trang_thai_filter)

    if ngay_nop_filter:
        dat_vong_cv = dat_vong_cv.filter(ngay_nop=ngay_nop_filter)
        khong_dat = khong_dat.filter(ngay_nop=ngay_nop_filter)

    context = {
        'dat_vong_cv': dat_vong_cv,
        'khong_dat': khong_dat,
        'search_query': q,
        'vi_tri_filter': vi_tri_filter,
        'ma_ho_so_filter': ma_ho_so_filter,
        'trang_thai_filter': trang_thai_filter,
        'ngay_nop_filter': ngay_nop_filter,
        'active_menu': 'tuyen_dung',
        'sub_menu': 'sang_loc_cv'
    }
    return render(request, 'recruitment/hr_sang_loc_cv.html', context)


# 8. QUẢN LÝ LỊCH PHỎNG VẤN (HR - Đã tích hợp bộ lọc tìm kiếm)
@login_required
def hr_lich_phong_van(request):
    if request.method == 'POST':
        ma_ho_so = request.POST.get('ma_ho_so')
        ngay_pv = request.POST.get('ngay_pv')
        gio_pv = request.POST.get('gio_pv')
        hinh_thuc = request.POST.get('hinh_thuc')
        dia_diem = request.POST.get('dia_diem')

        if ma_ho_so:
            ho_so = get_object_or_404(HoSoUngTuyen, ma_ho_so=ma_ho_so)
            ho_so.trang_thai = 'Đã lên lịch'
            ho_so.ngay_phong_van = ngay_pv
            ho_so.gio_phong_van = gio_pv
            ho_so.hinh_thuc_pv = hinh_thuc
            ho_so.dia_diem_pv = dia_diem
            ho_so.save()
            messages.success(request, f'Đã xếp lịch phỏng vấn cho hồ sơ {ma_ho_so}.')
            return redirect('recruitment:hr_lich_phong_van')

    # LẤY TẤT CẢ CÁC HỒ SƠ CHƯA BỊ KẾT LUẬN LÀ ĐẠT/KHÔNG ĐẠT HOẶC ĐÃ LÊN LỊCH
    danh_sach_lich = HoSoUngTuyen.objects.select_related('ma_ung_vien', 'ma_vi_tri', 'ma_dot').exclude(
        trang_thai__in=['Đạt', 'Không đạt', 'Không đạt vòng CV']
    ).order_by('-ngay_nop')

    # Bộ lọc GET trên giao diện
    q = request.GET.get('q', '').strip()
    vi_tri_filter = request.GET.get('vi_tri', '').strip()
    hinh_thuc_filter = request.GET.get('hinh_thuc', '').strip()
    trang_thai_filter = request.GET.get('trang_thai', '').strip()
    ngay_pv_filter = request.GET.get('ngay_pv', '').strip()

    if q:
        danh_sach_lich = danh_sach_lich.filter(
            Q(ma_ung_vien__ho_ten__icontains=q) |
            Q(ma_ung_vien__sdt__icontains=q) |
            Q(ma_ho_so__icontains=q)
        )
    if vi_tri_filter:
        danh_sach_lich = danh_sach_lich.filter(ma_vi_tri__ten_vi_tri=vi_tri_filter)
    if hinh_thuc_filter:
        danh_sach_lich = danh_sach_lich.filter(hinh_thuc_pv=hinh_thuc_filter)
    if trang_thai_filter:
        danh_sach_lich = danh_sach_lich.filter(trang_thai=trang_thai_filter)
    if ngay_pv_filter:
        danh_sach_lich = danh_sach_lich.filter(ngay_phong_van=ngay_pv_filter)

    context = {
        'danh_sach_lich': danh_sach_lich,
        'search_query': q,
        'vi_tri_filter': vi_tri_filter,
        'hinh_thuc_filter': hinh_thuc_filter,
        'trang_thai_filter': trang_thai_filter,
        'ngay_pv_filter': ngay_pv_filter,
        'active_menu': 'tuyen_dung',
        'sub_menu': 'lich_phong_van'
    }
    return render(request, 'recruitment/hr_lich_phong_van.html', context)


# 9. KẾT QUẢ TUYỂN DỤNG & ĐÁNH GIÁ (Đồng bộ dữ liệu thật từ Database)
@login_required
def hr_ket_qua_tuyen_dung(request):
    hom_nay = date.today()
    # XỬ LÝ LƯU KẾT QUẢ ĐÁNH GIÁ THẬT VÀO DATABASE KHI BẤM "LƯU ĐÁNH GIÁ"
    if request.method == 'POST' and 'ket_qua' in request.POST:
        ma_ho_so = request.POST.get('ma_ho_so')
        ket_qua_danh_gia = request.POST.get('ket_qua') # Nhận 'Đạt' hoặc 'Không đạt'

        if ma_ho_so and ket_qua_danh_gia:
            try:
                ho_so = HoSoUngTuyen.objects.get(ma_ho_so=ma_ho_so)
                ho_so.trang_thai = ket_qua_danh_gia # Lưu thẳng vào CSDL để load lại không bị mất
                ho_so.save()
                messages.success(request, f'Đã lưu đánh giá và cập nhật kết quả cho hồ sơ {ma_ho_so}.')
                return redirect('recruitment:hr_ket_qua_tuyen_dung')
            except HoSoUngTuyen.DoesNotExist:
                messages.error(request, 'Không tìm thấy hồ sơ.')

    # XỬ LÝ XÓA LỊCH SỬ KHI BẤM NÚT THÙNG RÁC
    if request.method == 'POST' and 'delete_ma_ho_so' in request.POST:
        del_ma_hs = request.POST.get('delete_ma_ho_so')
        try:
            ho_so_del = HoSoUngTuyen.objects.get(ma_ho_so=del_ma_hs)
            ho_so_del.trang_thai = 'Đã hủy' # Hoặc xóa tùy ý, ở đây ta đổi trạng thái để ẩn khỏi lịch sử
            ho_so_del.save()
            messages.success(request, f'Đã xóa hồ sơ {del_ma_hs} khỏi lịch sử.')
            return redirect('recruitment:hr_ket_qua_tuyen_dung')
        except HoSoUngTuyen.DoesNotExist:
            pass

    # Lấy danh sách chờ: Tất cả hồ sơ chưa chốt kết quả Đạt/Không đạt
    danh_sach_cho_pv = HoSoUngTuyen.objects.select_related('ma_ung_vien', 'ma_vi_tri', 'ma_dot').exclude(
        trang_thai__in=['Đạt', 'Không đạt', 'Không đạt vòng CV', 'Đã hủy']
    ).filter(
        # Chỉ đưa vào danh sách chờ đánh giá khi ngày phỏng vấn <= hôm nay (hoặc chưa xếp ngày)
        Q(ngay_phong_van__lte=hom_nay) | Q(ngay_phong_van__isnull=True)
    ).order_by('-ngay_nop')

    # Lấy lịch sử: Các hồ sơ đã có kết quả Đạt hoặc Không đạt
    danh_sach_ket_qua = HoSoUngTuyen.objects.select_related('ma_ung_vien', 'ma_vi_tri', 'ma_dot').filter(
        trang_thai__in=['Đạt', 'Không đạt']
    ).order_by('-ngay_nop')

    context = {
        'danh_sach_cho_pv': danh_sach_cho_pv,
        'danh_sach_ket_qua': danh_sach_ket_qua,
        'active_menu': 'tuyen_dung',
        'sub_menu': 'ket_qua'
    }
    return render(request, 'recruitment/hr_ket_qua_tuyen_dung.html', context)