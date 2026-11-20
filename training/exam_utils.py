
import random
import uuid
import unicodedata

from django.db import transaction

from .models import LichThi, DeThi, CauHoi


# Mỗi nhóm vị trí ứng với một đề nguồn
MA_DE_NGUON = {
    'phuc vu': 'BANKPV001',
    'pha chế': 'BANKPC001',
    'thu ngan': 'BANKTN001',
}


def chuan_hoa_vi_tri(vi_tri):
    """
    Chuẩn hóa dấu tiếng Việt, chữ hoa/thường
    và khoảng trắng trong tên vị trí.
    """
    chuoi = (vi_tri or '').strip().lower()
    chuoi = chuoi.replace('đ', 'd')

    chuoi = ''.join(
        c for c in unicodedata.normalize('NFD', chuoi)
        if unicodedata.category(c) != 'Mn'
    )

    return ' '.join(chuoi.split())


def lay_ma_de_nguon(vi_tri):
    """
    Tự xác định ngân hàng câu hỏi.
    Hỗ trợ các tên như:
    - Phục vụ
    - Phục vụ Part-time
    - Pha chế (Part-time)
    - Thu ngân Full-time
    """
    vi_tri_chuan = chuan_hoa_vi_tri(vi_tri)

    for ten_vi_tri, ma_de in MA_DE_NGUON.items():
        if ten_vi_tri in vi_tri_chuan:
            return ma_de

    raise ValueError(
        f'Chưa có ngân hàng câu hỏi cho '
        f'vị trí: {vi_tri}'
    )



@transaction.atomic
def tao_de_random(lich_thi, vi_tri, so_cau=10):
    """
    Tạo đề thi tổng kết từ ngân hàng theo vị trí.
    Mỗi lịch thi có một đề riêng.
    Đề được random một lần và lưu cố định.
    """

    # 1. Kiểm tra số câu hỏi
    if not isinstance(so_cau, int) or isinstance(so_cau, bool) or so_cau <= 0:
        raise ValueError(
            "Số câu thi phải là số nguyên dương."
        )

    # 2. Xác định ngân hàng theo vị trí
    ma_ngan_hang = {
        "Phục vụ": "BANKPV001",
        "Nhân viên phục vụ": "BANKPV001",
        "Pha chế": "BANKPC001",
        "Nhân viên pha chế": "BANKPC001",
        "Thu ngân": "BANKTN001",
        "Nhân viên thu ngân": "BANKTN001",
    }

    vi_tri = str(vi_tri or "").strip()

    ma_de_nguon = ma_ngan_hang.get(vi_tri)

    if not ma_de_nguon:
        raise ValueError(
            f"Chưa hỗ trợ ngân hàng câu hỏi cho vị trí: {vi_tri}"
        )

    # 3. Không tạo đề thật cho lịch ngân hàng
    if lich_thi.ma_lt.startswith("BANKLT"):
        raise ValueError(
            "Không được tạo đề thi trên lịch ngân hàng."
        )

    # 4. Lấy và khóa lịch thi hiện tại
    lich = (
        LichThi.objects
        .select_for_update()
        .get(pk=lich_thi.pk)
    )

    # 5. Mỗi lịch chỉ có một đề thi
    if DeThi.objects.filter(ma_lt=lich).exists():
        raise ValueError(
            "Lịch thi này đã được tạo đề trước đó."
        )

    # 6. Tìm đúng đề nguồn
    de_nguon = (
        DeThi.objects
        .filter(
            ma_dt=ma_de_nguon,
            ma_lt__ma_lt__startswith="BANKLT"
        )
        .first()
    )

    if de_nguon is None:
        raise ValueError(
            f"Không tìm thấy ngân hàng {ma_de_nguon} "
            f"cho vị trí {vi_tri}."
        )

    # 7. Lấy câu hỏi từ ngân hàng nguồn
    ngan_hang = list(
        CauHoi.objects.filter(
            ma_dt=de_nguon
        ).order_by("ma_ch")
    )

    if len(ngan_hang) < so_cau:
        raise ValueError(
            f"Ngân hàng {vi_tri} hiện có "
            f"{len(ngan_hang)} câu hỏi. "
            f"Cần tối thiểu {so_cau} câu."
        )

    # 8. Random không lặp câu
    cau_hoi_chon = random.sample(
        ngan_hang,
        so_cau
    )

    # 9. Tạo đề mới cho lịch thi nhân viên
    de_moi = DeThi.objects.create(
        ma_dt="DT" + uuid.uuid4().hex[:16],
        ma_lt=lich,
        ten_de_thi=f"Đề thi tổng kết {vi_tri}",
        thoi_luong=10 if so_cau == 5 else 30
    )

    # 10. Chia đều tổng điểm 100
    diem_moi_cau = 100.0 / so_cau

    # 11. Sao chép câu hỏi vào đề thi riêng
    ds_cau_hoi_moi = []

    for stt, cau in enumerate(cau_hoi_chon, start=1):

        ds_cau_hoi_moi.append(
            CauHoi(
                ma_ch=(
                    f"Q{stt:03d}"
                    f"{uuid.uuid4().hex[:15]}"
                ),
                ma_dt=de_moi,
                noi_dung_ch=cau.noi_dung_ch,
                dap_an_dung=cau.dap_an_dung,
                diem=diem_moi_cau
            )
        )

    CauHoi.objects.bulk_create(ds_cau_hoi_moi)

    # 12. Trả về đề thi vừa tạo
    return de_moi

