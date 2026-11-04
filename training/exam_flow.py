
# training/exam_flow.py

from .models import LichThi, DeThi, CauHoi, KetQuaThi
from .exam_student import DIEM_DAT


CHUA_THI = "chua_thi"
DA_XEP_LICH = "da_xep_lich"
THI_KHONG_DAT = "Thi Không Đạt"
THI_DAT = "Thi Đạt"


def lay_ket_qua_lich_thi(lich_thi):
    """
    Đọc điểm đã được exam_student.py lưu.
    Không chấm lại bài thi.

    Trả về None nếu bài chưa nộp đủ dữ liệu.
    """

    de_thi = (
        DeThi.objects
        .filter(ma_lt=lich_thi)
        .order_by("ma_dt")
        .first()
    )

    if de_thi is None:
        return None

    ma_cac_cau = list(
        CauHoi.objects.filter(
            ma_dt=de_thi
        ).values_list("ma_ch", flat=True)
    )

    if not ma_cac_cau:
        return None

    ds_kq = list(
        KetQuaThi.objects.filter(
            ma_lt=lich_thi,
            ma_ch_id__in=ma_cac_cau,
            lan_thi=1,
            thoi_gian_nop_bai__isnull=False
        )
    )

    # Mỗi câu trong đề phải có đúng một dòng kết quả.
    if len(ds_kq) != len(ma_cac_cau):
        return None

    if set(kq.ma_ch_id for kq in ds_kq) != set(ma_cac_cau):
        return None

    # Lấy tổng điểm máy chấm đã lưu.
    tong_diem = round(
        sum(kq.diem_so for kq in ds_kq),
        2
    )

    return {
        "tong_diem": tong_diem,
        "dat": tong_diem >= DIEM_DAT,
        "so_cau": len(ma_cac_cau),
    }


def lay_trang_thai_thi(nhan_vien):
    """
    Trạng thái để quản lý thao tác trên Dashboard.
    Một lịch thi thật tương ứng một lần thi.
    """

    ds_lich = list(
        LichThi.objects
        .filter(ma_nv=nhan_vien)
        .exclude(ma_lt__startswith="BANKLT")
        .order_by("-ngay_thi", "-ma_lt")
    )

    if not ds_lich:
        return {
            "trang_thai": CHUA_THI,
            "lich_thi": None,
            "ket_qua": None,
            "duoc_bo_tri_thi": True,
            "la_thi_lai": False,
        }

    # Đã từng đạt thì không cần thi lại nữa.
    for lich in ds_lich:
        ket_qua = lay_ket_qua_lich_thi(lich)

        if ket_qua and ket_qua["dat"]:
            return {
                "trang_thai": THI_DAT,
                "lich_thi": lich,
                "ket_qua": ket_qua,
                "duoc_bo_tri_thi": False,
                "la_thi_lai": False,
            }

    # Nếu chưa từng đạt, xét lịch gần nhất.
    lich_moi = ds_lich[0]
    ket_qua_moi = lay_ket_qua_lich_thi(lich_moi)

    if ket_qua_moi is None:
        return {
            "trang_thai": DA_XEP_LICH,
            "lich_thi": lich_moi,
            "ket_qua": None,
            "duoc_bo_tri_thi": False,
            "la_thi_lai": False,
        }

    return {
        "trang_thai": THI_KHONG_DAT,
        "lich_thi": lich_moi,
        "ket_qua": ket_qua_moi,
        "duoc_bo_tri_thi": True,
        "la_thi_lai": True,
    }
