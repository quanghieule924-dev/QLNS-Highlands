from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta


from django.http import JsonResponse
from django.views.decorators.http import require_GET
from employees.models import NhanVien



from django.db import transaction
import uuid
from django.contrib.auth import get_user_model
from .models import ThongBao


from .models import (
    HopDong,
    BHXH,
    PhuCap,
    PhucLoiHopDong,
    CheDoPhucLoi,
)

from .forms import (
    HopDongForm,
    GiaHanHopDongForm,
    ChamDutHopDongForm,
    CheDoPhucLoiForm,
)

from .decorators import role_required

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

def tao_ma_tu_dong(model, truong_ma, tien_to):
    """
    Tạo mã tự động theo tiền tố.
    Ví dụ: BH001, PC001, PLHD001.
    """
    cac_ma = model.objects.filter(
        **{f'{truong_ma}__startswith': tien_to}
    ).values_list(truong_ma, flat=True)

    so_lon_nhat = 0

    for ma in cac_ma:
        try:
            so = int(ma[len(tien_to):])
            so_lon_nhat = max(so_lon_nhat, so)
        except (ValueError, TypeError):
            continue

    return f'{tien_to}{so_lon_nhat + 1:03d}'

def luu_thong_tin_lien_quan(request, hop_dong):
    """
    Lưu thông tin BHXH, phụ cấp và phúc lợi của hợp đồng.
    """

    # ==========================================
    # 1. LƯU THÔNG TIN BẢO HIỂM XÃ HỘI
    # ==========================================
#Cập nhật ngày 8/11
    co_tham_gia_bhxh = request.POST.get('co_tham_gia_bhxh') == 'on'

    if co_tham_gia_bhxh:

        # Kiểm tra hợp đồng đã có thông tin BHXH chưa
        bhxh = BHXH.objects.filter(
            hop_dong=hop_dong
        ).first()

        # Nếu chưa có thì tạo mới
        if bhxh is None:
            bhxh = BHXH(
                mabh=tao_ma_tu_dong(BHXH, 'mabh', 'BH'),
                hop_dong=hop_dong
            )

        # Nếu đã có thì cập nhật đối tượng cũ
        # Không tạo đối tượng mới với mã BHXH cũ
        bhxh.ma_so_bh = request.POST.get('ma_so_bh')
        bhxh.muc_dong = request.POST.get('muc_dong')
        bhxh.ngay_tham_gia = request.POST.get('ngay_tham_gia')
        bhxh.trang_thai = request.POST.get(
            'trang_thai_bhxh',
            'dang_tham_gia'
        )

        bhxh.full_clean()
        bhxh.save()

    else:
        # Nếu không tham gia thì xóa thông tin BHXH
        BHXH.objects.filter(hop_dong=hop_dong).delete()


    # ==========================================
    # 2. LƯU CÁC KHOẢN PHỤ CẤP
    # ==========================================

    # Xóa phụ cấp cũ để cập nhật lại theo dữ liệu form
    PhuCap.objects.filter(hop_dong=hop_dong).delete()

    cac_loai_pc = request.POST.getlist('loai_pc[]')
    cac_gia_tri_pc = request.POST.getlist('gia_tri_pc[]')
    cac_thang_pc = request.POST.getlist('thang_ap_dung[]')

    for loai_pc, gia_tri, thang in zip(
        cac_loai_pc,
        cac_gia_tri_pc,
        cac_thang_pc
    ):
        # Bỏ qua dòng hoàn toàn trống
        if not loai_pc.strip() and not gia_tri.strip() and not thang.strip():
            continue

        # Nếu đã nhập một phần thì báo lỗi
        if not loai_pc.strip() or not gia_tri.strip() or not thang.strip():
            raise ValidationError(
                'Vui lòng nhập đầy đủ loại phụ cấp, giá trị và tháng áp dụng.'
            )

        phu_cap = PhuCap(
            mapc=tao_ma_tu_dong(PhuCap, 'mapc', 'PC'),
            hop_dong=hop_dong,
            loai_pc=loai_pc.strip(),
            gia_tri=gia_tri,
            thang_ap_dung=thang
        )

        phu_cap.full_clean()
        phu_cap.save()


    # ==========================================
    # 3. LƯU CÁC CHẾ ĐỘ PHÚC LỢI
    # ==========================================

    # Xóa các chế độ phúc lợi cũ
    PhucLoiHopDong.objects.filter(hop_dong=hop_dong).delete()

    # Lấy danh sách mã chế độ phúc lợi được chọn
    cac_phuc_loi = request.POST.getlist('che_do_phuc_loi[]')

    # Loại bỏ mã bị trùng
    cac_phuc_loi = list(dict.fromkeys(cac_phuc_loi))

    for ma_pl in cac_phuc_loi:
        if ma_pl:
            phuc_loi = PhucLoiHopDong(
                maplhd=tao_ma_tu_dong(
                    PhucLoiHopDong,
                    'maplhd',
                    'PLHD'
                ),
                hop_dong=hop_dong,
                che_do_id=ma_pl,
                gia_tri=None
            )

            phuc_loi.full_clean()
            phuc_loi.save()

# =========================================================
# 1. DANH SÁCH HỢP ĐỒNG
# =========================================================

@role_required('admin', 'employee')
def danh_sach_hop_dong(request):
    # Tạo thông báo hợp đồng sắp hết hạn cho Admin
    if request.user.role == 'admin':
        tao_thong_bao_hop_dong_sap_het_han()

    # Tự động cập nhật trạng thái hợp đồng theo ngày bắt đầu
    ngay_hien_tai = timezone.localdate()

    # Hợp đồng đã ký và đã đến ngày bắt đầu
    HopDong.objects.filter(
        trang_thai_hd='da_ky_cho_hieu_luc',
        ngay_bat_dau__lte=ngay_hien_tai
    ).update(
        trang_thai_hd='dang_hieu_luc'
    )

    # Hợp đồng đang hiệu lực nhưng đã hết hạn
    HopDong.objects.filter(
        trang_thai_hd='dang_hieu_luc',
        loai_hd='co_thoi_han',
        ngay_ket_thuc__lt=ngay_hien_tai
    ).update(
        trang_thai_hd='da_het_han'
    )

    # # Hợp đồng đã ký nhưng chưa đến ngày bắt đầu
    HopDong.objects.filter(
        trang_thai_hd='dang_hieu_luc',
        ngay_ky__isnull=False,
        ngay_bat_dau__gt=ngay_hien_tai
    ).update(
        trang_thai_hd='da_ky_cho_hieu_luc'
    )

    # Quản lý xem tất cả hợp đồng
    if request.user.role == 'admin':
        hop_dongs = HopDong.objects.select_related(
            'nhan_vien',
            'hop_dong_truoc'
        ).all()

    # Nhân viên chỉ xem hợp đồng của mình
    else:
        hop_dongs = HopDong.objects.select_related(
            'nhan_vien',
            'hop_dong_truoc'
        ).filter(
            nhan_vien__tai_khoan=request.user
        )

    # Tìm kiếm
    tu_khoa = request.GET.get('q', '').strip()

    if tu_khoa:
        hop_dongs = hop_dongs.filter(
            Q(mahd__icontains=tu_khoa) |
            Q(so_hd__icontains=tu_khoa)
        )

    # Lọc trạng thái
    trang_thai = request.GET.get('trang_thai', '')

    if trang_thai:
        hop_dongs = hop_dongs.filter(
            trang_thai_hd=trang_thai
        )

    # Lọc loại hợp đồng
    loai_hd = request.GET.get('loai_hd', '')

    if loai_hd:
        hop_dongs = hop_dongs.filter(
            loai_hd=loai_hd
        )

    context = {
        'hop_dongs': hop_dongs,
        'tu_khoa': tu_khoa,
        'trang_thai': trang_thai,
        'loai_hd': loai_hd,
        'trang_thai_choices': HopDong.TRANG_THAI_CHOICES,
        'loai_hd_choices': HopDong.LOAI_HD_CHOICES,
        'active_menu': 'contracts',
    }

    return render(
        request,
        'contracts/danh_sach_hop_dong.html',

        context

    )

# =========================================================
# 2. THÊM HỢP ĐỒNG
# =========================================================

@role_required('admin')
def them_hop_dong(request):

    if request.method == 'POST':
        form = HopDongForm(request.POST)

        if form.is_valid():
            hop_dong = form.save(commit=False)

            # Tự động tạo mã hợp đồng
            if not hop_dong.mahd:
                hop_dong_cuoi = HopDong.objects.order_by('-mahd').first()

                if hop_dong_cuoi and hop_dong_cuoi.mahd.startswith('HD'):
                    so_thu_tu = int(hop_dong_cuoi.mahd[2:]) + 1
                else:
                    so_thu_tu = 1

                hop_dong.mahd = f'HD{so_thu_tu:03d}'

            # Hợp đồng mới luôn ở trạng thái chờ nhân viên ký
            hop_dong.trang_thai_hd = 'cho_ky'

            try:
                with transaction.atomic():
                    hop_dong.full_clean()
                    hop_dong.save()

                    # Lưu thông tin BHXH, phụ cấp và phúc lợi
                    luu_thong_tin_lien_quan(request, hop_dong)
                    nhan_vien = hop_dong.nhan_vien

                    if nhan_vien.trang_thai in ['Tập sự', 'Tap_su']:
                        nhan_vien.trang_thai = 'Chờ hợp đồng'
                        nhan_vien.save(update_fields=['trang_thai'])

                messages.success(
                    request,
                    'Thêm hợp đồng thành công!'
                )

                return redirect('contracts:danh_sach_hop_dong')

            except ValidationError as e:
                form.add_error(None, e)

    else:
        form = HopDongForm()

    return render(
        request,
        'contracts/form_hop_dong.html',
        {
            'form': form,
            'tieu_de': 'Thêm hợp đồng',
            'active_menu': 'contracts',

            # Danh sách chế độ phúc lợi để hiển thị trên form
            'danh_sach_che_do': CheDoPhucLoi.objects.all(),

            # Hợp đồng mới chưa có thông tin BHXH
            'bhxh': None,

            # Hợp đồng mới chưa có phụ cấp
            'danh_sach_phu_cap': [],

            # Chưa có chế độ phúc lợi nào được chọn
            'phuc_loi_da_chon': [],
        }
    )

# =========================================================
# 3. CHI TIẾT HỢP ĐỒNG
# =========================================================
@role_required('admin', 'employee')
def chi_tiet_hop_dong(request, mahd):

    hop_dongs = HopDong.objects.select_related(
        'nhan_vien',
        'hop_dong_truoc'
    )

    # Nhân viên chỉ được xem hợp đồng của mình
    if request.user.role == 'employee':
        hop_dongs = hop_dongs.filter(
            nhan_vien__tai_khoan=request.user
        )

    hop_dong = get_object_or_404(
        hop_dongs,
        mahd=mahd
    )

    # Lấy thông tin BHXH
    bhxh = BHXH.objects.filter(
        hop_dong=hop_dong
    ).first()

    # Lấy danh sách phụ cấp
    danh_sach_phu_cap = PhuCap.objects.filter(
        hop_dong=hop_dong
    )

    # Lấy danh sách phúc lợi áp dụng
    danh_sach_phuc_loi = PhucLoiHopDong.objects.filter(
        hop_dong=hop_dong
    ).select_related('che_do')



    context = {
        'hop_dong': hop_dong,
        'bhxh': bhxh,
        'danh_sach_phu_cap': danh_sach_phu_cap,
        'danh_sach_phuc_loi': danh_sach_phuc_loi,
        'active_menu': 'contracts',
    }

    return render(
        request,
        'contracts/chi_tiet_hop_dong.html',
        context
    )
# =========================================================
# 4. CHỈNH SỬA HỢP ĐỒNG
# =========================================================

@role_required('admin')
def sua_hop_dong(request, mahd):

    hop_dong = get_object_or_404(
        HopDong,
        mahd=mahd
    )

    # Chỉ cho phép sửa hợp đồng chờ ký hoặc đang hiệu lực
    if hop_dong.trang_thai_hd not in ['cho_ky', 'dang_hieu_luc']:
        messages.error(
            request,
            'Không thể chỉnh sửa hợp đồng đã hết hạn hoặc đã chấm dứt!'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong.mahd
        )

    if request.method == 'POST':
        form = HopDongForm(
            request.POST,
            instance=hop_dong
        )

        if form.is_valid():
            hop_dong = form.save(commit=False)

            try:
                # Lưu hợp đồng và thông tin liên quan cùng một giao dịch
                with transaction.atomic():
                    hop_dong.full_clean()
                    hop_dong.save()

                    # Cập nhật BHXH, phụ cấp và phúc lợi
                    luu_thong_tin_lien_quan(request, hop_dong)

                messages.success(
                    request,
                    'Cập nhật hợp đồng thành công!'
                )

                return redirect(
                    'contracts:chi_tiet_hop_dong',
                    mahd=hop_dong.mahd
                )

#Cập nhât
            except ValidationError as e:
                form.add_error(None, "; ".join(e.messages))

    else:
        form = HopDongForm(instance=hop_dong)

    # Lấy thông tin BHXH của hợp đồng
    bhxh = BHXH.objects.filter(
        hop_dong=hop_dong
    ).first()

    # Lấy danh sách phụ cấp của hợp đồng
    danh_sach_phu_cap = PhuCap.objects.filter(
        hop_dong=hop_dong
    )

    # Lấy danh sách mã chế độ phúc lợi đã được áp dụng
    phuc_loi_da_chon = list(
        PhucLoiHopDong.objects.filter(
            hop_dong=hop_dong
        ).values_list('che_do_id', flat=True)
    )

    # Lấy toàn bộ danh mục chế độ phúc lợi
    danh_sach_che_do = CheDoPhucLoi.objects.all()

    return render(
        request,
        'contracts/form_hop_dong.html',
        {
            'form': form,
            'tieu_de': 'Chỉnh sửa hợp đồng',
            'hop_dong': hop_dong,
            'active_menu': 'contracts',

            # Dữ liệu BHXH
            'bhxh': bhxh,

            # Danh sách phụ cấp
            'danh_sach_phu_cap': danh_sach_phu_cap,

            # Danh sách mã phúc lợi đã chọn
            'phuc_loi_da_chon': phuc_loi_da_chon,

            # Danh mục phúc lợi
            'danh_sach_che_do': danh_sach_che_do,
        }
    )
# =========================================================
# 5. XÓA HỢP ĐỒNG
# =========================================================

@role_required('admin')
def xoa_hop_dong(request, mahd):

    hop_dong = get_object_or_404(
        HopDong,
        mahd=mahd
    )

    # Chỉ cho phép xóa hợp đồng đang chờ ký
    if hop_dong.trang_thai_hd != 'cho_ky':
        messages.error(
            request,
            'Chỉ được xóa hợp đồng đang ở trạng thái chờ ký!'
        )
        return redirect('contracts:danh_sach_hop_dong')

    if request.method == 'POST':
        hop_dong.delete()

        messages.success(
            request,
            'Xóa hợp đồng thành công!'
        )

        return redirect('contracts:danh_sach_hop_dong')

    return render(
        request,
        'contracts/xac_nhan_xoa_hop_dong.html',
        {
            'hop_dong': hop_dong,
        }
    )


# =========================================================
# 6. HỢP ĐỒNG SẮP HẾT HẠN
# =========================================================

@role_required('admin', 'employee')
def hop_dong_sap_het_han(request):
    # Tự động gọi tạo thông báo hợp đồng sắp hết hạn nếu là admin
    if request.user.role == 'admin':
        tao_thong_bao_hop_dong_sap_het_han()

    # Lấy toàn bộ hợp đồng đang hiệu lực, có thời hạn
    hop_dongs_qs = HopDong.objects.select_related(
        'nhan_vien',
        'hop_dong_truoc'
    ).filter(
        trang_thai_hd='dang_hieu_luc',
        loai_hd='co_thoi_han'
    ).order_by('ngay_ket_thuc')

    # Nhân viên chỉ xem hợp đồng của chính mình
    if request.user.role == 'employee':
        hop_dongs_qs = hop_dongs_qs.filter(
            nhan_vien__tai_khoan=request.user
        )

    # Lọc danh sách thực tế các hợp đồng thực sự sắp hết hạn
    hop_dongs = [
        hd for hd in hop_dongs_qs
        if hd.sap_het_han
    ]

    # Tìm kiếm theo từ khóa (nếu có nhập)
    tu_khoa = request.GET.get('q', '').strip()
    if tu_khoa:
        tu_khoa_lower = tu_khoa.lower()
        hop_dongs = [
            hd for hd in hop_dongs
            if tu_khoa_lower in str(hd.mahd).lower()
            or tu_khoa_lower in str(hd.so_hd).lower()
            or (hd.nhan_vien and tu_khoa_lower in str(hd.nhan_vien.ho_ten).lower())
        ]

    return render(
        request,
        'contracts/hop_dong_sap_het_han.html',
        {
            'hop_dongs': hop_dongs,
            'tu_khoa': tu_khoa,
            'active_menu': 'contracts',
        }
    )


# =========================================================
# 9. NHÂN VIÊN ký hợp đồng
# =========================================================
@role_required('employee')
def ky_hop_dong(request, mahd):
    if request.method != 'POST':
        return redirect('contracts:chi_tiet_hop_dong', mahd=mahd)

    # Chỉ nhân viên được ký hợp đồng của chính mình
    hop_dong = get_object_or_404(
        HopDong,
        mahd=mahd,
        nhan_vien__tai_khoan=request.user
    )

    # Chỉ được ký hợp đồng đang chờ ký
    if hop_dong.trang_thai_hd != 'cho_ky':
        messages.error(
            request,
            'Hợp đồng này không ở trạng thái chờ ký.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=mahd
        )

    # Lấy ngày ký thực tế
    ngay_ky = timezone.localdate()

    try:
        with transaction.atomic():
            hop_dong.ngay_ky = ngay_ky

            # Xác định trạng thái dựa trên ngày bắt đầu hợp đồng
            if ngay_ky < hop_dong.ngay_bat_dau:
                hop_dong.trang_thai_hd = 'da_ky_cho_hieu_luc'
            else:
                hop_dong.trang_thai_hd = 'dang_hieu_luc'

            hop_dong.full_clean()
            hop_dong.save()

        messages.success(
            request,
            'Bạn đã xác nhận ký hợp đồng thành công!'
        )

    except ValidationError as e:
        messages.error(request, str(e))

    return redirect(
        'contracts:chi_tiet_hop_dong',
        mahd=mahd
    )

################################################################
######################################################
@role_required('admin')
def cham_dut_hop_dong(request, mahd):

    hop_dong = get_object_or_404(HopDong, mahd=mahd)

    # Chỉ được chấm dứt hợp đồng đang có hiệu lực
    if hop_dong.trang_thai_hd != 'dang_hieu_luc':
        messages.error(
            request,
            'Chỉ được chấm dứt hợp đồng đang có hiệu lực!'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=mahd
        )

    if request.method == 'POST':
        form = ChamDutHopDongForm(
            request.POST,
            instance=hop_dong
        )

        if form.is_valid():
            hop_dong = form.save(commit=False)
            hop_dong.trang_thai_hd = 'da_cham_dut'

            try:
                hop_dong.full_clean()
                hop_dong.save()

                messages.success(
                    request,
                    'Chấm dứt hợp đồng thành công!'
                )

                return redirect(
                    'contracts:chi_tiet_hop_dong',
                    mahd=mahd
                )

            except ValidationError as e:
                form.add_error(None, e)

    else:
        form = ChamDutHopDongForm(instance=hop_dong)

    return render(
        request,
        'contracts/form_cham_dut_hop_dong.html',
        {
            'form': form,
            'hop_dong': hop_dong,
            'tieu_de': 'Chấm dứt hợp đồng',
            'active_menu': 'contracts',
        }
    )

###########################################
#GIA HẠN HỢP ĐỒNG
#################################################

@role_required('admin')
def gia_han_hop_dong(request, mahd):
    hop_dong_cu = get_object_or_404(HopDong, mahd=mahd)

    # 1. Kiểm tra trạng thái hợp đồng
    if hop_dong_cu.trang_thai_hd != 'dang_hieu_luc':
        messages.error(
            request,
            'Chỉ có thể gia hạn hợp đồng đang có hiệu lực.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong_cu.mahd
        )

    # 2. Chỉ gia hạn hợp đồng có thời hạn
    if hop_dong_cu.loai_hd != 'co_thoi_han':
        messages.error(
            request,
            'Chỉ có thể gia hạn hợp đồng có thời hạn.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong_cu.mahd
        )

    # 3. Chỉ gia hạn hợp đồng sắp hết hạn
    if not hop_dong_cu.sap_het_han:
        messages.error(
            request,
            'Hợp đồng chưa đến thời điểm được gia hạn.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong_cu.mahd
        )

    # Ngày bắt đầu hợp đồng mới
    ngay_bat_dau_moi = (
        hop_dong_cu.ngay_ket_thuc + timedelta(days=1)
    )

    if request.method == 'POST':
        form = GiaHanHopDongForm(request.POST)

        if form.is_valid():
            hop_dong_moi = form.save(commit=False)

            # Kế thừa thông tin từ hợp đồng cũ
            hop_dong_moi.nhan_vien = hop_dong_cu.nhan_vien
            hop_dong_moi.hop_dong_truoc = hop_dong_cu
            hop_dong_moi.loai_hd = hop_dong_cu.loai_hd

            # Tự động tạo mã hợp đồng mới
            hop_dong_moi.mahd = tao_ma_tu_dong(
                HopDong, 'mahd', 'HD'
            )

            # Ngày bắt đầu là ngày sau khi hợp đồng cũ kết thúc
            hop_dong_moi.ngay_bat_dau = ngay_bat_dau_moi

            # Hợp đồng mới phải được ký
            hop_dong_moi.ngay_ky = None
            hop_dong_moi.trang_thai_hd = 'cho_ky'

            try:
                with transaction.atomic():

                    # Lưu hợp đồng mới
                    hop_dong_moi.full_clean()
                    hop_dong_moi.save()

                    # Lưu BHXH, phụ cấp và phúc lợi theo thông tin trên form
                    luu_thong_tin_lien_quan(request, hop_dong_moi)


                messages.success(
                    request,
                    'Tạo hợp đồng gia hạn thành công. '
                    'Thông tin BHXH, phụ cấp và phúc lợi đã được kế thừa. '
                    'Nhân viên cần ký hợp đồng mới.'
                )

                return redirect(
                    'contracts:chi_tiet_hop_dong',
                    mahd=hop_dong_moi.mahd
                )

            except ValidationError as e:
                form.add_error(None, e)


    else:

        form = GiaHanHopDongForm(initial={

            'hinh_thuc_luong': hop_dong_cu.hinh_thuc_luong,

            'muc_luong': hop_dong_cu.muc_luong,

        })

    # Lấy thông tin BHXH của hợp đồng cũ

    bhxh = BHXH.objects.filter(

        hop_dong=hop_dong_cu

    ).first()

    # Lấy danh sách phụ cấp của hợp đồng cũ

    danh_sach_phu_cap = PhuCap.objects.filter(

        hop_dong=hop_dong_cu

    )

    # Lấy danh sách tất cả chế độ phúc lợi

    danh_sach_che_do = CheDoPhucLoi.objects.all()

    # Lấy mã các chế độ phúc lợi đang áp dụng

    phuc_loi_da_chon = list(

        PhucLoiHopDong.objects.filter(

            hop_dong=hop_dong_cu

        ).values_list('che_do_id', flat=True)

    )
    return render(
        request,
        'contracts/form_gia_han_hop_dong.html',
        {
            'form': form,
            'hop_dong_cu': hop_dong_cu,
            'ngay_bat_dau_moi': ngay_bat_dau_moi,

            # Thông tin kế thừa từ hợp đồng cũ
            'bhxh': bhxh,
            'danh_sach_phu_cap': danh_sach_phu_cap,
            'danh_sach_che_do': danh_sach_che_do,
            'phuc_loi_da_chon': phuc_loi_da_chon,
        }
    )
# =========================================================
# HÀM TẠO THÔNG BÁO HỢP ĐỒNG SẮP HẾT HẠN
# =========================================================

def tao_thong_bao_hop_dong_sap_het_han():

    User = get_user_model()

    # Lấy tất cả tài khoản Admin
    admins = User.objects.filter(role='admin')

    # Lấy hợp đồng đang hiệu lực, có thời hạn
    hop_dongs = HopDong.objects.filter(
        trang_thai_hd='dang_hieu_luc',
        loai_hd='co_thoi_han'
    ).select_related('nhan_vien')

    # Chỉ giữ hợp đồng còn tối đa 30 ngày
    hop_dongs = [
        hd for hd in hop_dongs
        if hd.sap_het_han
    ]

    # Tạo thông báo cho từng Admin
    for hd in hop_dongs:

        noi_dung = (
            f"Hợp đồng {hd.mahd} của nhân viên "
            f"{hd.nhan_vien.ho_ten} sắp hết hạn vào ngày "
            f"{hd.ngay_ket_thuc.strftime('%d/%m/%Y')}."
        )

        for admin in admins:

            ThongBao.objects.get_or_create(
                hop_dong=hd,
                nguoi_nhan=admin,
                defaults={
                    'matb': 'TB' + uuid.uuid4().hex[:18].upper(),
                    'noi_dung': noi_dung,
                    'trang_thai': 'chua_doc',
                }
            )



#
#Tạo chức năng nhấn vào thông báo
#
@role_required('admin')
def mo_thong_bao(request, matb):

    thong_bao = get_object_or_404(
        ThongBao,
        matb=matb,
        nguoi_nhan=request.user
    )

    # Đánh dấu đã đọc
    if thong_bao.trang_thai == 'chua_doc':
        thong_bao.trang_thai = 'da_doc'
        thong_bao.save(update_fields=['trang_thai'])

    # Mở chi tiết hợp đồng
    return redirect(
        'contracts:chi_tiet_hop_dong',
        mahd=thong_bao.hop_dong.mahd
    )


# =========================================================
# 10. QUẢN LÝ CHẾ ĐỘ PHÚC LỢI
# =========================================================

# Hàm phụ lấy danh sách phúc lợi có phân trang
def _get_che_do_phuc_loi_page(request):
    che_do_phuc_loi = CheDoPhucLoi.objects.all()
    paginator = Paginator(che_do_phuc_loi, 8)

    trang_hien_tai = request.GET.get('page', 1)

    return paginator.get_page(trang_hien_tai)


# 10.1. Danh sách chế độ phúc lợi
@role_required('admin')
def danh_sach_che_do_phuc_loi(request):
    page_obj = _get_che_do_phuc_loi_page(request)

    return render(
        request,
        'contracts/danh_sach_che_do_phuc_loi.html',
        {
            'page_obj': page_obj,
            'che_do_phuc_loi': page_obj,
            'active_menu': 'contracts',
        }
    )


# 10.2. Thêm chế độ phúc lợi
@role_required('admin')
def them_che_do_phuc_loi(request):
    if request.method == 'POST':
        form = CheDoPhucLoiForm(request.POST)

        if form.is_valid():
            che_do = form.save(commit=False)

            # Tự động tạo mã phúc lợi
            che_do.mapl = 'PL' + uuid.uuid4().hex[:8].upper()

            try:
                che_do.full_clean()
                che_do.save()

                messages.success(
                    request,
                    'Thêm chế độ phúc lợi thành công!'
                )

                return redirect(
                    'contracts:danh_sach_che_do_phuc_loi'
                )

            except ValidationError as e:
                form.add_error(None, e)

    else:
        form = CheDoPhucLoiForm()

    page_obj = _get_che_do_phuc_loi_page(request)

    return render(
        request,
        'contracts/danh_sach_che_do_phuc_loi.html',
        {
            'page_obj': page_obj,
            'che_do_phuc_loi': page_obj,
            'form': form,
            'tieu_de': 'Thêm chế độ phúc lợi',
            'mo_popup': True,
            'active_menu': 'contracts',
        }
    )


# 10.3. Sửa chế độ phúc lợi
@role_required('admin')
def sua_che_do_phuc_loi(request, mapl):
    che_do = get_object_or_404(
        CheDoPhucLoi,
        mapl=mapl
    )

    if request.method == 'POST':
        form = CheDoPhucLoiForm(
            request.POST,
            instance=che_do
        )

        if form.is_valid():
            che_do = form.save(commit=False)

            try:
                che_do.full_clean()
                che_do.save()

                messages.success(
                    request,
                    'Cập nhật chế độ phúc lợi thành công!'
                )

                return redirect(
                    'contracts:danh_sach_che_do_phuc_loi'
                )

            except ValidationError as e:
                form.add_error(None, e)

    else:
        form = CheDoPhucLoiForm(instance=che_do)

    page_obj = _get_che_do_phuc_loi_page(request)

    return render(
        request,
        'contracts/danh_sach_che_do_phuc_loi.html',
        {
            'page_obj': page_obj,
            'che_do_phuc_loi': page_obj,
            'form': form,
            'che_do': che_do,
            'tieu_de': 'Sửa chế độ phúc lợi',
            'mo_popup': True,
            'active_menu': 'contracts',
        }
    )

# =========================================================
# 11. TỔNG QUAN HỢP ĐỒNG VÀ PHÚC LỢI
# =========================================================

@role_required('admin')
def tong_quan_hop_dong(request):

    # 1. Tổng số hợp đồng
    tong_so_hop_dong = HopDong.objects.count()

    # 2. Số hợp đồng chờ ký
    hop_dong_cho_ky = HopDong.objects.filter(
        trang_thai_hd='cho_ky'
    ).count()

    # 3. Số hợp đồng đang hiệu lực
    hop_dong_dang_hieu_luc = HopDong.objects.filter(
        trang_thai_hd='dang_hieu_luc'
    ).count()

    # 4. Danh sách hợp đồng
    danh_sach_hop_dong = HopDong.objects.select_related(
        'nhan_vien'
    ).order_by('-ngay_bat_dau')[:5]

    # 5. Danh sách hợp đồng sắp hết hạn
    tat_ca_hop_dong = HopDong.objects.select_related(
        'nhan_vien'
    ).filter(
        trang_thai_hd='dang_hieu_luc',
        loai_hd='co_thoi_han'
    )

    hop_dong_sap_het_han = [
        hd for hd in tat_ca_hop_dong
        if hd.sap_het_han
    ]

    # Sắp xếp theo ngày hết hạn gần nhất
    hop_dong_sap_het_han.sort(
        key=lambda hd: hd.ngay_ket_thuc
    )

    tong_hop_dong_sap_het_han = len(
        hop_dong_sap_het_han
    )

    return render(
        request,
        'contracts/tong_quan_hop_dong.html',
        {
            'tong_so_hop_dong': tong_so_hop_dong,
            'hop_dong_cho_ky': hop_dong_cho_ky,
            'hop_dong_dang_hieu_luc': hop_dong_dang_hieu_luc,
            'tong_hop_dong_sap_het_han': tong_hop_dong_sap_het_han,

            'danh_sach_hop_dong': danh_sach_hop_dong,
            'danh_sach_hop_dong_sap_het_han': (
                hop_dong_sap_het_han[:5]
            ),

            'active_menu': 'contracts',
        }
    )




@require_GET
def lay_thong_tin_nhan_vien(request, manv):
    try:
        nhan_vien = NhanVien.objects.get(manv=manv)

        return JsonResponse({
            'ngay_sinh': (
                nhan_vien.ngay_sinh.strftime('%d/%m/%Y')
                if nhan_vien.ngay_sinh else ''
            ),
            'gioi_tinh': nhan_vien.gioi_tinh or '',
            'sdt': nhan_vien.sdt or '',
            'email': nhan_vien.email or '',
            'vi_tri': nhan_vien.vi_tri or '',
        })

    except NhanVien.DoesNotExist:
        return JsonResponse(
            {'error': 'Không tìm thấy nhân viên'},
            status=404
        )


@login_required
def phuc_loi_cua_toi(request):
    # Chỉ cho phép nhân viên truy cập
    if request.user.role != 'employee':
        return HttpResponseForbidden("Bạn không có quyền truy cập.")

    # Lấy hồ sơ nhân viên liên kết với tài khoản đang đăng nhập
    try:
        nhan_vien = request.user.nhan_vien
    except NhanVien.DoesNotExist:
        return render(request, 'contracts/phuc_loi_cua_toi.html', {
            'phuc_lois': [],
            'thong_bao': 'Tài khoản chưa được liên kết với hồ sơ nhân viên.'
        })

    # Chỉ lấy hợp đồng đang có hiệu lực của nhân viên này
    hop_dongs = (
        HopDong.objects
        .filter(
            nhan_vien=nhan_vien,
            trang_thai_hd='dang_hieu_luc'
        )
        .prefetch_related(
            'phuc_loi_hop_dong__che_do'
        )
    )

    # Lấy danh sách phúc lợi thuộc các hợp đồng đang hiệu lực
    phuc_lois = []

    for hop_dong in hop_dongs:
        for item in hop_dong.phuc_loi_hop_dong.all():
            phuc_lois.append({
                'hop_dong': hop_dong,
                'che_do': item.che_do,
                'gia_tri': item.gia_tri,
            })

    context = {
        'phuc_lois': phuc_lois,
        'hop_dongs': hop_dongs,
        'thong_bao': (
            'Chưa có chế độ phúc lợi nào được áp dụng '
            'cho hợp đồng đang có hiệu lực.'
            if not phuc_lois else ''
        )
    }

    return render(
        request,
        'contracts/phuc_loi_cua_toi.html',
        context
    )