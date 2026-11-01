
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.exceptions import ValidationError

from .models import HopDong
from .forms import HopDongForm


# =========================================================
# 1. DANH SÁCH HỢP ĐỒNG
# =========================================================

@login_required
def danh_sach_hop_dong(request):

    hop_dongs = HopDong.objects.select_related(
        'nhan_vien',
        'hop_dong_truoc'
    ).all()

    # Tìm kiếm theo số hợp đồng hoặc mã hợp đồng
    tu_khoa = request.GET.get('q', '').strip()

    if tu_khoa:
        hop_dongs = hop_dongs.filter(
            Q(mahd__icontains=tu_khoa) |
            Q(so_hd__icontains=tu_khoa)
        )

    # Lọc theo trạng thái
    trang_thai = request.GET.get('trang_thai', '')

    if trang_thai:
        hop_dongs = hop_dongs.filter(
            trang_thai_hd=trang_thai
        )

    # Lọc theo loại hợp đồng
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

@login_required
def them_hop_dong(request):

    if request.method == 'POST':
        form = HopDongForm(request.POST)

        if form.is_valid():
            hop_dong = form.save(commit=False)

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
        }
    )


# =========================================================
# 3. CHI TIẾT HỢP ĐỒNG
# =========================================================

@login_required
def chi_tiet_hop_dong(request, mahd):

    hop_dong = get_object_or_404(
        HopDong.objects.select_related(
            'nhan_vien',
            'hop_dong_truoc'
        ),
        mahd=mahd
    )

    return render(
        request,
        'contracts/chi_tiet_hop_dong.html',
        {
            'hop_dong': hop_dong,
        }
    )


# =========================================================
# 4. CHỈNH SỬA HỢP ĐỒNG
# =========================================================

@login_required
def sua_hop_dong(request, mahd):

    hop_dong = get_object_or_404(
        HopDong,
        mahd=mahd
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
        }
    )


# =========================================================
# 5. XÓA HỢP ĐỒNG
# =========================================================

@login_required
def xoa_hop_dong(request, mahd):

    hop_dong = get_object_or_404(
        HopDong,
        mahd=mahd
    )

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

@login_required
def hop_dong_sap_het_han(request):

    hop_dongs = HopDong.objects.select_related(
        'nhan_vien'
    ).filter(
        trang_thai_hd='dang_hieu_luc',
        loai_hd='co_thoi_han'
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
