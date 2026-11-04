
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
def tao_de_random(lich_thi, vi_tri, so_cau=5):
    """
    Tạo đề thi riêng từ ngân hàng câu hỏi.
    Random một lần, sau đó lưu cố định.
    """

    if not isinstance(so_cau, int) or so_cau <= 0:
        raise ValueError(
            'Số câu thi phải là số nguyên dương.'
        )

    # Tuyệt đối không tạo đề thật cho lịch nguồn
    if lich_thi.ma_lt.startswith('BANKLT'):
        raise ValueError(
            'Không được tạo đề thi trên lịch ngân hàng.'
        )

    # Khóa lịch trong giao dịch để hạn chế tạo trùng
    lich = (
        LichThi.objects
        .select_for_update()
        .get(pk=lich_thi.pk)
    )

    if DeThi.objects.filter(ma_lt=lich).exists():
        raise ValueError(
            'Lịch thi này đã có đề thi.'
        )

    # Tự tìm ngân hàng theo vị trí
    ma_de_nguon = lay_ma_de_nguon(vi_tri)

    try:
        de_nguon = DeThi.objects.get(
            ma_dt=ma_de_nguon,
            ma_lt__ma_lt__startswith='BANKLT'
        )

    except DeThi.DoesNotExist:
        raise ValueError(
            f'Chưa tạo ngân hàng đề {ma_de_nguon}.'
        )

    # Lấy các câu hỏi nguồn
    ngan_hang = list(
        CauHoi.objects.filter(
            ma_dt=de_nguon
        ).order_by('ma_ch')
    )

    if len(ngan_hang) < so_cau:
        raise ValueError(
            f'Ngân hàng {de_nguon.ten_de_thi} '
            f'chỉ có {len(ngan_hang)} câu hỏi. '
            f'Cần tối thiểu {so_cau} câu.'
        )

    # Chọn ngẫu nhiên không trùng câu
    cau_hoi_chon = random.sample(
        ngan_hang,
        so_cau
    )

    # Tạo mã đề mới, tối đa 20 ký tự
    ma_de_moi = 'DT' + uuid.uuid4().hex[:16]

    de_moi = DeThi.objects.create(
        ma_dt=ma_de_moi,
        ma_lt=lich,
        ten_de_thi=f'Đề thi tổng kết {vi_tri}',
        thoi_luong=10 if so_cau == 5 else 30
    )

    # Điểm các câu cộng lại bằng 100
    diem_moi_cau = 100.0 / so_cau

    for stt, cau in enumerate(cau_hoi_chon, start=1):

        # Q001... Q002... giúp lưu thứ tự
        # câu hỏi đã được random
        ma_cau_moi = (
            f'Q{stt:03d}'
            f'{uuid.uuid4().hex[:15]}'
        )

        CauHoi.objects.create(
            ma_ch=ma_cau_moi,
            ma_dt=de_moi,
            noi_dung_ch=cau.noi_dung_ch,
            dap_an_dung=cau.dap_an_dung,
            diem=diem_moi_cau
        )

    return de_moi
