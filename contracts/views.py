from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.forms import HiddenInput
from django import forms



from django.db import transaction
import uuid


from .models import (
    HopDong,
    YeuCauNghiTruocHan,
    YeuCauChinhSuaHD,
)

from .forms import (
    HopDongForm,
    GiaHanHopDongForm,
    YeuCauNghiTruocHanForm,
    YeuCauChinhSuaHDForm,
    DuyetYeuCauNghiTruocHanForm,
    DuyetYeuCauChinhSuaHDForm,
    ChamDutHopDongForm,
)

from .decorators import role_required

# =========================================================
# 1. DANH SÁCH HỢP ĐỒNG
# =========================================================

@role_required('admin', 'employee')
def danh_sach_hop_dong(request):

    # Tự động cập nhật trạng thái hợp đồng theo ngày bắt đầu
    ngay_hien_tai = timezone.localdate()

    # Hợp đồng đã ký nhưng chưa đến ngày bắt đầu
    HopDong.objects.filter(
        trang_thai_hd='dang_hieu_luc',
        ngay_ky__isnull=False,
        ngay_bat_dau__gt=ngay_hien_tai
    ).update(
        trang_thai_hd='da_ky_cho_hieu_luc'
    )

    # Hợp đồng đã ký và đã đến ngày bắt đầu
    HopDong.objects.filter(
        trang_thai_hd='da_ky_cho_hieu_luc',
        ngay_bat_dau__lte=ngay_hien_tai
    ).update(
        trang_thai_hd='dang_hieu_luc'
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
            # Hợp đồng mới luôn ở trạng thái chờ nhân viên ký
            hop_dong.trang_thai_hd = 'cho_ky'

            try:
                hop_dong.full_clean()
                hop_dong.save()

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

    context = {
        'hop_dong': hop_dong,
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
                hop_dong.full_clean()
                hop_dong.save()

                messages.success(
                    request,
                    'Cập nhật hợp đồng thành công!'
                )

                return redirect(
                    'contracts:chi_tiet_hop_dong',
                    mahd=hop_dong.mahd
                )

            except ValidationError as e:
                form.add_error(None, e)

    else:
        form = HopDongForm(instance=hop_dong)

    return render(
        request,
        'contracts/form_hop_dong.html',
        {
            'form': form,
            'tieu_de': 'Chỉnh sửa hợp đồng',
            'hop_dong': hop_dong,
            'active_menu': 'contracts',
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

    hop_dongs = HopDong.objects.select_related(
        'nhan_vien'
    ).filter(
        trang_thai_hd='dang_hieu_luc',
        loai_hd='co_thoi_han'
    )

    # Nhân viên chỉ xem hợp đồng của mình
    if request.user.role == 'employee':
        hop_dongs = hop_dongs.filter(
            nhan_vien__tai_khoan=request.user
        )

    hop_dongs = [
        hop_dong
        for hop_dong in hop_dongs
        if hop_dong.sap_het_han
    ]

    return render(
        request,
        'contracts/hop_dong_sap_het_han.html',
        {
            'hop_dongs': hop_dongs,
        }
    )

# # =========================================================
# # 7. NHÂN VIÊN GỬI YÊU CẦU NGHỈ TRƯỚC HẠN
# # =========================================================
#
# @role_required('employee')
# def gui_yeu_cau_nghi(request):
#
#     nhan_vien = getattr(request.user, 'nhan_vien', None)
#
#     if nhan_vien is None:
#         messages.error(
#             request,
#             'Tài khoản chưa được liên kết với hồ sơ nhân viên.'
#         )
#         return redirect('contracts:danh_sach_hop_dong')
#
#     if request.method == 'POST':
#         form = YeuCauNghiTruocHanForm(
#             request.POST,
#             nhan_vien=nhan_vien
#         )
#
#         if form.is_valid():
#
#             yeu_cau = form.save(commit=False)
#
#             yeu_cau.ngay_gui = timezone.localdate()
#             yeu_cau.trang_thai_duyet = 'cho_duyet'
#             yeu_cau.ngay_duyet = None
#
#             try:
#                 yeu_cau.full_clean()
#                 yeu_cau.save()
#
#                 messages.success(
#                     request,
#                     'Gửi yêu cầu nghỉ trước hạn thành công!'
#                 )
#
#                 return redirect('contracts:danh_sach_hop_dong')
#
#             except ValidationError as e:
#                 form.add_error(None, e)
#
#     else:
#         form = YeuCauNghiTruocHanForm(
#             nhan_vien=nhan_vien
#         )
#
#     return render(
#         request,
#         'contracts/form_yeu_cau_nghi.html',
#         {
#             'form': form,
#             'tieu_de': 'Gửi yêu cầu nghỉ trước hạn',
#         }
#     )
#

# =========================================================
# 8. NHÂN VIÊN GỬI YÊU CẦU CHỈNH SỬA HỢP ĐỒNG
# =========================================================

@role_required('employee')
def gui_yeu_cau_chinh_sua(request, mahd):
    messages.warning(request, 'Chức năng yêu cầu chỉnh sửa hợp đồng hiện đã tạm khóa.')

    return redirect(
        'contracts:chi_tiet_hop_dong',
        mahd=mahd
    )

    nhan_vien = getattr(request.user, 'nhan_vien', None)

    if nhan_vien is None:
        messages.error(
            request,
            'Tài khoản chưa được liên kết với hồ sơ nhân viên.'
        )
        return redirect('contracts:danh_sach_hop_dong')

    # Lấy đúng hợp đồng thuộc nhân viên đang đăng nhập
    hop_dong = get_object_or_404(
        HopDong,
        mahd=mahd,
        nhan_vien=nhan_vien
    )

    # Chỉ cho phép yêu cầu chỉnh sửa hợp đồng đang chờ ký
    if hop_dong.trang_thai_hd != 'cho_ky':
        messages.error(
            request,
            'Chỉ có thể yêu cầu chỉnh sửa hợp đồng đang chờ ký.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=mahd
        )

    if request.method == 'POST':
        form = YeuCauChinhSuaHDForm(request.POST)
        print("FORM CLASS:", YeuCauChinhSuaHDForm)
        print("FORM FIELDS:", list(form.fields.keys()))
        print("FORM ERRORS:", form.errors)

        if form.is_valid():
            yeu_cau = form.save(commit=False)

            # Tự động tạo mã yêu cầu chỉnh sửa
            yeu_cau.macs = 'YCS' + uuid.uuid4().hex[:8].upper()

            # Tự động gán thông tin yêu cầu
            yeu_cau.hop_dong = hop_dong
            yeu_cau.ngay_yeu_cau = timezone.localdate()
            yeu_cau.trang_thai_cs = 'cho_duyet'

            try:
                yeu_cau.full_clean()
                yeu_cau.save()

                messages.success(
                    request,
                    'Gửi yêu cầu chỉnh sửa hợp đồng thành công!'
                )

                return redirect(
                    'contracts:chi_tiet_hop_dong',
                    mahd=mahd
                )

            except ValidationError as e:
                form.add_error(None, e)

        else:
            print("FORM ERRORS:", form.errors)

    else:
        form = YeuCauChinhSuaHDForm()

    return render(
        request,
        'contracts/form_yeu_cau_chinh_sua.html',
        {
            'form': form,
            'tieu_de': 'Gửi yêu cầu chỉnh sửa hợp đồng',
            'hop_dong': hop_dong,
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

    # Kiểm tra trạng thái hợp đồng
    if hop_dong_cu.trang_thai_hd != 'dang_hieu_luc':
        messages.error(
            request,
            'Chỉ có thể gia hạn hợp đồng đang có hiệu lực.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong_cu.mahd
        )

    # Chỉ gia hạn hợp đồng có thời hạn
    if hop_dong_cu.loai_hd != 'co_thoi_han':
        messages.error(
            request,
            'Chỉ có thể gia hạn hợp đồng có thời hạn.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong_cu.mahd
        )

    # Chỉ gia hạn hợp đồng sắp hết hạn
    if not hop_dong_cu.sap_het_han:
        messages.error(
            request,
            'Hợp đồng chưa đến thời điểm được gia hạn.'
        )
        return redirect(
            'contracts:chi_tiet_hop_dong',
            mahd=hop_dong_cu.mahd
        )

    if request.method == 'POST':
        form = GiaHanHopDongForm(request.POST)

        if form.is_valid():
            hop_dong_moi = form.save(commit=False)

            # Kế thừa thông tin từ hợp đồng cũ
            hop_dong_moi.nhan_vien = hop_dong_cu.nhan_vien
            hop_dong_moi.hop_dong_truoc = hop_dong_cu
            hop_dong_moi.loai_hd = hop_dong_cu.loai_hd

            # Ngày bắt đầu là ngày sau khi hợp đồng cũ kết thúc
            hop_dong_moi.ngay_bat_dau = (
                hop_dong_cu.ngay_ket_thuc + timedelta(days=1)
            )

            # Hợp đồng mới phải được ký
            hop_dong_moi.ngay_ky = None
            hop_dong_moi.trang_thai_hd = 'cho_ky'

            try:
                hop_dong_moi.full_clean()
                hop_dong_moi.save()

                messages.success(
                    request,
                    'Tạo hợp đồng gia hạn thành công. '
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

    return render(
        request,
        'contracts/form_gia_han_hop_dong.html',
        {
            'form': form,
            'hop_dong_cu': hop_dong_cu,
            'ngay_bat_dau_moi': (
                hop_dong_cu.ngay_ket_thuc + timezone.timedelta(days=1)
            ),
        }
    )