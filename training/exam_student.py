
import re
import uuid

from datetime import datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.utils import timezone
from django.views.decorators.http import require_POST

from employees.models import NhanVien

from .models import (
    ChuongTrinhTapSu,
    BaiHoc,
    TienDoTapSu,
    LichThi,
    DeThi,
    CauHoi,
    KetQuaThi,
)


# ==========================================
# 1. CẤU HÌNH CA THI
# ==========================================

CA_THI = {
    'Sang': (9, 0, 10, 0),
    'Chieu': (14, 0, 15, 0),
    'Toi': (19, 0, 20, 0),

    # Hỗ trợ dữ liệu cũ trong database
    'Ca Sáng (09:00 - 10:00)': (9, 0, 10, 0),
    'Ca Chiều (14:00 - 15:00)': (14, 0, 15, 0),
    'Ca Tối (19:00 - 20:00)': (19, 0, 20, 0),
}

DIEM_DAT = 80


# ==========================================
# 2. XÁC ĐỊNH NHÂN VIÊN ĐĂNG NHẬP
# ==========================================

def lay_nhan_vien(request):

    if request.user.role != 'employee':
        raise PermissionDenied(
            'Chỉ nhân viên được làm bài thi.'
        )

    return get_object_or_404(
        NhanVien,
        tai_khoan=request.user
    )


# ==========================================
# 3. KIỂM TRA HOÀN THÀNH OJT
# ==========================================

def kiem_tra_ojt(nhan_vien):

    chuong_trinh = (
        ChuongTrinhTapSu.objects
        .filter(
            ma_nv=nhan_vien,
            trang_thai_duyet='Đã duyệt'
        )
        .order_by('-ma_ct')
        .first()
    )

    if chuong_trinh is None:
        return False

    ds_bai_hoc = list(
        BaiHoc.objects.filter(
            ma_ct=chuong_trinh
        )
    )

    if not ds_bai_hoc:
        return False

    ds_danh_gia = (
        TienDoTapSu.objects
        .filter(
            ma_nv=nhan_vien,
            ma_bh__in=ds_bai_hoc
        )
        .order_by('ngay_danh_gia', 'ma_td')
    )

    danh_gia_moi_nhat = {}

    for item in ds_danh_gia:
        danh_gia_moi_nhat[item.ma_bh_id] = item

    for bai in ds_bai_hoc:

        ket_qua = danh_gia_moi_nhat.get(
            bai.ma_bh
        )

        if ket_qua is None:
            return False

        trang_thai = (
            ket_qua.trang_thai_danh_gia or ''
        ).strip().casefold()

        if trang_thai != 'đạt':
            return False

    return True


# ==========================================
# 4. LẤY LỊCH THI VÀ ĐỀ THI RIÊNG
# ==========================================

def lay_du_lieu_thi(request, ma_lt):

    nhan_vien = lay_nhan_vien(request)

    # Không cho nhân viên truy cập lịch ngân hàng
    lich_thi = get_object_or_404(
        LichThi.objects.exclude(
            ma_lt__startswith='BANKLT'
        ),
        ma_lt=ma_lt,
        ma_nv=nhan_vien
    )

    if not kiem_tra_ojt(nhan_vien):
        raise PermissionDenied(
            'Bạn chưa hoàn thành 100% OJT.'
        )

    de_thi = get_object_or_404(
        DeThi,
        ma_lt=lich_thi
    )

    ds_cau_hoi = list(
        CauHoi.objects.filter(
            ma_dt=de_thi
        ).order_by('ma_ch')
    )

    if not ds_cau_hoi:
        raise PermissionDenied(
            'Đề thi chưa có câu hỏi.'
        )

    return (
        nhan_vien,
        lich_thi,
        de_thi,
        ds_cau_hoi
    )


# ==========================================
# 5. XÁC ĐỊNH GIỜ BẮT ĐẦU, KẾT THÚC CA
# ==========================================

def lay_gio_ca_thi(lich_thi):

    ca = CA_THI.get(
        (lich_thi.ca_thi or '').strip()
    )

    if ca is None:
        raise PermissionDenied(
            'Ca thi chưa được cấu hình.'
        )

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

    return bat_dau, ket_thuc


# ==========================================
# 6. QUẢN LÝ SESSION BÀI THI
# ==========================================

def khoa_session(lich_thi):

    return f'bai_thi_{lich_thi.ma_lt}'


def da_nop_bai(lich_thi):

    return KetQuaThi.objects.filter(
        ma_lt=lich_thi,
        lan_thi=1
    ).exists()


def lay_han_nop(request, lich_thi, de_thi):

    du_lieu = request.session.get(
        khoa_session(lich_thi)
    )

    if du_lieu is None:
        return None

    bat_dau_lam = datetime.fromisoformat(
        du_lieu['bat_dau']
    )

    _, ket_thuc_ca = lay_gio_ca_thi(
        lich_thi
    )

    het_thoi_luong = (
        bat_dau_lam
        + timedelta(minutes=de_thi.thoi_luong)
    )

    # Không cho làm vượt quá giờ kết thúc ca
    return min(
        het_thoi_luong,
        ket_thuc_ca
    )


# ==========================================
# 7. TÁCH CÂU HỎI VÀ PHƯƠNG ÁN
# ==========================================

def tach_cau_hoi(cau):

    noi_dung = []
    dap_an = {}

    for dong in cau.noi_dung_ch.splitlines():

        match = re.match(
            r'^\s*([A-D])\s*[.)]\s*(.+)$',
            dong
        )

        if match:
            dap_an[match.group(1)] = match.group(2)
        else:
            noi_dung.append(dong)

    if set(dap_an.keys()) != {
        'A', 'B', 'C', 'D'
    }:
        raise ValueError(
            f'Câu hỏi {cau.ma_ch} '
            f'chưa đủ bốn đáp án.'
        )

    return {
        'ma': cau.ma_ch,
        'noi_dung': '\n'.join(noi_dung),
        'lua_chon': [
            {
                'ma': ma,
                'noi_dung': dap_an[ma]
            }
            for ma in ('A', 'B', 'C', 'D')
        ]
    }


# ==========================================
# 8. CHẤM ĐIỂM VÀ LƯU KẾT QUẢ
# ==========================================

def cham_va_luu_bai(
    request,
    lich_thi,
    ds_cau_hoi,
    dap_an_da_chon
):

    with transaction.atomic():

        if da_nop_bai(lich_thi):
            return

        thoi_gian_nop = timezone.now()

        for cau in ds_cau_hoi:

            lua_chon = dap_an_da_chon.get(
                cau.ma_ch, ''
            )

            if lua_chon not in (
                'A', 'B', 'C', 'D'
            ):
                lua_chon = ''

            dung = (
                lua_chon == cau.dap_an_dung
            )

            KetQuaThi.objects.create(
                ma_kq=(
                    'KQ'
                    + uuid.uuid4().hex[:16]
                ),
                ma_lt=lich_thi,
                ma_ch=cau,
                lan_thi=1,
                diem_so=(
                    cau.diem if dung else 0
                ),
                dap_an_da_chon=lua_chon,
                thoi_gian_nop_bai=thoi_gian_nop,
                ket_qua=(
                    'Đúng' if dung else 'Sai'
                )
            )

    request.session.pop(
        khoa_session(lich_thi), None
    )

    request.session.modified = True


# ==========================================
# 9. TRANG NHÂN VIÊN LÀM BÀI THI
# ==========================================

@login_required
def lam_bai_thi(request, ma_lt):

    (
        nhan_vien,
        lich_thi,
        de_thi,
        ds_cau_hoi
    ) = lay_du_lieu_thi(
        request,
        ma_lt
    )

    if da_nop_bai(lich_thi):
        return redirect(
            'training:ket_qua_bai_thi',
            ma_lt=ma_lt
        )

    hien_tai = timezone.now()

    dau_ca, cuoi_ca = lay_gio_ca_thi(
        lich_thi
    )

    key = khoa_session(lich_thi)

    # Chưa đến giờ thi
    if hien_tai < dau_ca:
        return redirect(
            'training:lich_thi_nhan_vien'
        )

    # Bắt đầu lượt thi
    if key not in request.session:

        if hien_tai >= cuoi_ca:
            return redirect(
                'training:lich_thi_nhan_vien'
            )

        request.session[key] = {
            'bat_dau': hien_tai.isoformat(),
            'dap_an': {}
        }

        request.session.modified = True

    du_lieu = request.session[key]

    han_nop = lay_han_nop(
        request,
        lich_thi,
        de_thi
    )

    # Hết giờ sẽ chấm bài theo đáp án đã lưu
    if hien_tai >= han_nop:

        cham_va_luu_bai(
            request,
            lich_thi,
            ds_cau_hoi,
            du_lieu.get('dap_an', {})
        )

        return redirect(
            'training:ket_qua_bai_thi',
            ma_lt=ma_lt
        )

    # Nhân viên xác nhận nộp bài
    if request.method == 'POST':

        dap_an = dict(
            du_lieu.get('dap_an', {})
        )

        for cau in ds_cau_hoi:

            lua_chon = request.POST.get(
                f'cau_{cau.ma_ch}'
            )

            if lua_chon in (
                'A', 'B', 'C', 'D'
            ):
                dap_an[cau.ma_ch] = lua_chon

        cham_va_luu_bai(
            request,
            lich_thi,
            ds_cau_hoi,
            dap_an
        )

        return redirect(
            'training:ket_qua_bai_thi',
            ma_lt=ma_lt
        )

    # Chuyển dữ liệu câu hỏi sang giao diện
    cau_hoi_hien_thi = [
        tach_cau_hoi(cau)
        for cau in ds_cau_hoi
    ]

    so_giay_con = max(
        0,
        int(
            (
                han_nop - timezone.now()
            ).total_seconds()
        )
    )

    return render(
        request,
        'training/lam_bai_thi.html',
        {
            'nhan_vien': nhan_vien,
            'lich_thi': lich_thi,
            'de_thi': de_thi,
            'cau_hoi': cau_hoi_hien_thi,
            'tong_cau': len(ds_cau_hoi),
            'so_giay_con': so_giay_con,
            'dap_an_da_luu': (
                du_lieu.get('dap_an', {})
            ),
        }
    )


# ==========================================
# 10. TỰ LƯU ĐÁP ÁN KHI NHÂN VIÊN CHỌN
# ==========================================

@login_required
@require_POST
def luu_dap_an_thi(request, ma_lt):

    (
        nhan_vien,
        lich_thi,
        de_thi,
        ds_cau_hoi
    ) = lay_du_lieu_thi(
        request,
        ma_lt
    )

    if da_nop_bai(lich_thi):
        return JsonResponse(
            {
                'ok': False,
                'error': 'Bài thi đã được nộp.'
            },
            status=403
        )

    key = khoa_session(lich_thi)

    if key not in request.session:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Chưa bắt đầu thi.'
            },
            status=403
        )

    han_nop = lay_han_nop(
        request,
        lich_thi,
        de_thi
    )

    if timezone.now() >= han_nop:
        return JsonResponse(
            {
                'ok': False,
                'error': 'Đã hết giờ làm bài.'
            },
            status=403
        )

    ma_cau = request.POST.get(
        'ma_cau', ''
    )

    dap_an = request.POST.get(
        'dap_an', ''
    )

    ma_cau_hop_le = {
        cau.ma_ch
        for cau in ds_cau_hoi
    }

    if (
        ma_cau not in ma_cau_hop_le
        or dap_an not in ('A', 'B', 'C', 'D')
    ):
        return JsonResponse(
            {
                'ok': False,
                'error': 'Đáp án không hợp lệ.'
            },
            status=400
        )

    du_lieu = request.session[key]

    du_lieu['dap_an'][ma_cau] = dap_an

    request.session[key] = du_lieu
    request.session.modified = True

    return JsonResponse({
        'ok': True,
        'message': 'Đã lưu đáp án.'
    })


# ==========================================
# 11. TRANG KẾT QUẢ THI
# ==========================================


@login_required
def ket_qua_bai_thi(request, ma_lt):

    nhan_vien = lay_nhan_vien(request)

    lich_thi = get_object_or_404(
        LichThi.objects.exclude(
            ma_lt__startswith='BANKLT'
        ),
        ma_lt=ma_lt,
        ma_nv=nhan_vien
    )

    de_thi = get_object_or_404(
        DeThi,
        ma_lt=lich_thi
    )

    # Kết quả được lưu sau khi nộp bài
    ds_ket_qua = list(
        KetQuaThi.objects
        .select_related('ma_ch')
        .filter(
            ma_lt=lich_thi,
            ma_ch__ma_dt=de_thi,
            lan_thi=1
        )
        .order_by('ma_ch__ma_ch')
    )

    if not ds_ket_qua:
        return redirect(
            'training:lich_thi_nhan_vien'
        )

    # Tính điểm và số câu
    tong_diem = round(
        sum(kq.diem_so for kq in ds_ket_qua), 1
    )

    diem_toi_da = round(
        sum(kq.ma_ch.diem for kq in ds_ket_qua), 1
    )

    so_cau_dung = 0
    chi_tiet = []

    for stt, kq in enumerate(ds_ket_qua, start=1):

        cau_hoi = kq.ma_ch

        dap_an_chon = (
            kq.dap_an_da_chon or ''
        ).strip().upper()

        dap_an_dung = (
            cau_hoi.dap_an_dung or ''
        ).strip().upper()

        dung = (
            dap_an_chon == dap_an_dung
        )

        if dung:
            so_cau_dung += 1

        # Nội dung trong CauHoi đang có dạng:
        # Câu hỏi
        # A. ...
        # B. ...
        # C. ...
        # D. ...
        try:
            cau_da_tach = tach_cau_hoi(cau_hoi)

            noi_dung = cau_da_tach['noi_dung']

            lua_chon = {
                item['ma']: item['noi_dung']
                for item in cau_da_tach['lua_chon']
            }

        except ValueError:
            noi_dung = cau_hoi.noi_dung_ch
            lua_chon = {}

        chi_tiet.append({
            'stt': stt,
            'noi_dung': noi_dung,
            'dap_an_chon': dap_an_chon,
            'dap_an_dung': dap_an_dung,
            'noi_dung_chon': lua_chon.get(
                dap_an_chon, 'Chưa trả lời'
            ),
            'noi_dung_dung': lua_chon.get(
                dap_an_dung, ''
            ),
            'dung': dung,
            'diem': kq.diem_so,
        })

    tong_cau = len(ds_ket_qua)
    so_cau_sai = tong_cau - so_cau_dung

    # Ngưỡng đạt từ 80 điểm trở lên,
    # áp dụng cho thang điểm 100.
    dat = tong_diem >= 80

    # Một lịch thi tương ứng một lần thi
    # trong luồng hiện tại.
    lan_thi = ds_ket_qua[0].lan_thi

    ngay_nop = max(
        (
            kq.thoi_gian_nop_bai
            for kq in ds_ket_qua
            if kq.thoi_gian_nop_bai
        ),
        default=None
    )

    return render(
        request,
        'training/ket_qua_bai_thi.html',
        {
            'nhan_vien': nhan_vien,
            'lich_thi': lich_thi,
            'de_thi': de_thi,
            'tong_diem': tong_diem,
            'diem_toi_da': diem_toi_da,
            'dat': dat,
            'tong_cau': tong_cau,
            'so_cau_dung': so_cau_dung,
            'so_cau_sai': so_cau_sai,
            'chi_tiet': chi_tiet,
            'lan_thi': lan_thi,
            'ngay_nop': ngay_nop,
        }
    )

