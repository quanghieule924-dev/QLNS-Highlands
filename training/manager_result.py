
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404

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


@login_required
def trang_thai_ho_so(request, ma_nv):

    # Chỉ quản lý được xem trang
    if request.user.role != 'admin':
        raise PermissionDenied(
            'Chỉ quản lý được xem hồ sơ.'
        )

    nhan_vien = get_object_or_404(
        NhanVien,
        manv=ma_nv
    )

    chuong_trinh = (
        ChuongTrinhTapSu.objects
        .filter(ma_nv=nhan_vien)
        .order_by('-ma_ct')
        .first()
    )

    trang_thai_duyet = False
    tong_bai = 0
    so_bai_dat = 0
    tien_do = 0

    if chuong_trinh:

        trang_thai_duyet = (
            chuong_trinh.trang_thai_duyet
            == 'Đã duyệt'
        )

        ds_bai = list(
            BaiHoc.objects.filter(
                ma_ct=chuong_trinh
            )
        )

        tong_bai = len(ds_bai)

        ds_danh_gia = (
            TienDoTapSu.objects
            .filter(
                ma_nv=nhan_vien,
                ma_bh__in=ds_bai
            )
            .order_by(
                'ngay_danh_gia',
                'ma_td'
            )
        )

        danh_gia_moi_nhat = {}

        for item in ds_danh_gia:
            danh_gia_moi_nhat[
                item.ma_bh_id
            ] = item

        for bai in ds_bai:

            ket_qua = danh_gia_moi_nhat.get(
                bai.ma_bh
            )

            if ket_qua and (
                ket_qua.trang_thai_danh_gia or ''
            ).strip().casefold() == 'đạt':
                so_bai_dat += 1

        if tong_bai:
            tien_do = round(
                so_bai_dat * 100 / tong_bai,
                1
            )

    hoan_thanh_ojt = (
        trang_thai_duyet
        and tong_bai > 0
        and so_bai_dat == tong_bai
    )

    # Lấy tất cả lịch thi THẬT của nhân viên
    lich_thi_that = list(
        LichThi.objects
        .filter(ma_nv=nhan_vien)
        .exclude(ma_lt__startswith='BANKLT')
        .order_by('-ngay_thi', '-ma_lt')
    )

    cac_lan_thi = []

    for lich in lich_thi_that:

        de_thi = DeThi.objects.filter(
            ma_lt=lich
        ).first()

        if not de_thi:
            continue

        ket_qua = list(
            KetQuaThi.objects
            .filter(
                ma_lt=lich,
                ma_ch__ma_dt=de_thi
            )
            .select_related('ma_ch')
            .order_by('lan_thi', 'ma_ch__ma_ch')
        )

        # Một lịch có thể chứa nhiều lượt
        # nếu dữ liệu sau này có thi lại.
        cac_lan = sorted({
            kq.lan_thi
            for kq in ket_qua
        })

        for lan in cac_lan:

            ds_lan = [
                kq for kq in ket_qua
                if kq.lan_thi == lan
            ]

            tong_cau_de = CauHoi.objects.filter(
                ma_dt=de_thi
            ).count()

            # Chỉ xem là đã nộp đủ khi có
            # kết quả cho tất cả câu trong đề.
            if len(ds_lan) != tong_cau_de:
                continue

            diem = round(
                sum(kq.diem_so for kq in ds_lan),
                1
            )

            ngay_nop = max(
                (
                    kq.thoi_gian_nop_bai
                    for kq in ds_lan
                    if kq.thoi_gian_nop_bai
                ),
                default=None
            )

            cac_lan_thi.append({
                'lich': lich,
                'de': de_thi,
                'lan': lan,
                'diem': diem,
                'dat': diem >= 80,
                'ngay_nop': ngay_nop,
            })

    # Lần có điểm cao nhất dùng để xem
    # nhân viên đã từng đạt hay chưa.
    lan_tot_nhat = max(
        cac_lan_thi,
        key=lambda item: item['diem'],
        default=None
    )

    diem_tot_nhat = (
        lan_tot_nhat['diem']
        if lan_tot_nhat else None
    )

    da_dat_thi = any(
        item['dat']
        for item in cac_lan_thi
    )

    # Hoàn thành thi không đồng nghĩa
    # hợp đồng đã được phê duyệt.
    du_dieu_kien_xet_duyet = (
        hoan_thanh_ojt and da_dat_thi
    )

    return render(
        request,
        'training/trang_thai_ho_so.html',
        {
            'active_menu': 'training',
            'nhan_vien': nhan_vien,
            'chuong_trinh': chuong_trinh,
            'trang_thai_duyet': trang_thai_duyet,
            'tong_bai': tong_bai,
            'so_bai_dat': so_bai_dat,
            'tien_do': tien_do,
            'hoan_thanh_ojt': hoan_thanh_ojt,
            'cac_lan_thi': cac_lan_thi,
            'so_lan_thi': len(cac_lan_thi),
            'lan_tot_nhat': lan_tot_nhat,
            'diem_tot_nhat': diem_tot_nhat,
            'da_dat_thi': da_dat_thi,
            'du_dieu_kien_xet_duyet':
                du_dieu_kien_xet_duyet,
        }
    )
