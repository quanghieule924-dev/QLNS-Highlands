"""Tính lương dự kiến từ chấm công và hợp đồng.
Phiếu lương đã chốt là dữ liệu lịch sử độc lập.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q

from employees.models import NhanVien
from attendance.models import DuLieuChamCong, YeuCauDieuChinhCong
from contracts.models import HopDong, PhuCap
from .models import CauHinhLuong


def D(value):
    return Decimal(str(value if value is not None else 0))


CENT = D("0.01")


def preview(period):
    # ==========================================
    # 1. XÁC ĐỊNH KỲ LƯƠNG
    # ==========================================
    start = date(period.year, period.month, 1)

    end = date(
        period.year,
        period.month,
        monthrange(period.year, period.month)[1]
    )

    employees = list(
        NhanVien.objects.all().order_by("manv")
    )

    # ==========================================
    # 2. LẤY HỢP ĐỒNG CÓ HIỆU LỰC TRONG KỲ
    # ==========================================
    contracts = (
        HopDong.objects
        .filter(ngay_bat_dau__lte=end)
        .filter(
            Q(ngay_ket_thuc__isnull=True)
            | Q(ngay_ket_thuc__gte=start)
        )
        .exclude(
            trang_thai_hd__in=[
                "cho_ky",
                "da_het_han",
                "da_cham_dut"
            ]
        )
        .order_by("-ngay_bat_dau", "-mahd")
    )

    contract_map = {}

    for contract in contracts:
        contract_map.setdefault(
            contract.nhan_vien_id,
            contract
        )

    # Cấu hình lương chỉ là tùy chọn.
    # Không bắt buộc đối với nhân viên trả theo giờ.
    config_map = {
        cfg.nhan_vien_id: cfg
        for cfg in CauHinhLuong.objects.filter(
            nhan_vien__in=employees
        )
    }

    # ==========================================
    # 3. LẤY PHỤ CẤP TỪ HỢP ĐỒNG
    # ==========================================
    allowance_by_contract = {}

    month_key = start.strftime("%Y-%m")

    allowances = PhuCap.objects.filter(
        hop_dong_id__in=[
            contract.pk
            for contract in contract_map.values()
        ],
        thang_ap_dung=month_key
    ).values(
        "hop_dong_id",
        "gia_tri"
    )

    for item in allowances:
        contract_id = item["hop_dong_id"]

        allowance_by_contract[contract_id] = (
            allowance_by_contract.get(
                contract_id,
                D(0)
            ) + D(item["gia_tri"])
        )

    # ==========================================
    # 4. TỔNG HỢP GIỜ CÔNG SAU CHECK-OUT
    # ==========================================
    records = (
        DuLieuChamCong.objects
        .filter(
            ma_lich_lam__ngay_lam__range=(
                start,
                end
            )
        )
        .select_related(
            "ma_lich_lam__ma_ca_lam",
            "ma_lich_lam__ma_nv"
        )
    )

    time_map = {}

    for record in records:
        checkin = record.time_checkin
        checkout = record.time_checkout

        # Chỉ tính khi có đầy đủ giờ vào và giờ ra.
        if checkin is None or checkout is None:
            continue

        if checkout <= checkin:
            continue

        shift = record.ma_lich_lam.ma_ca_lam

        if shift is None:
            continue

        begin = shift.start_time
        finish = shift.end_time

        if begin is None or finish is None:
            continue

        # Tính thời lượng ca, hỗ trợ ca qua đêm.
        planned_minutes = (
            (
                finish.hour * 60 + finish.minute
            )
            -
            (
                begin.hour * 60 + begin.minute
            )
        ) % (24 * 60)

        # Ca có giờ bắt đầu bằng giờ kết thúc
        # được xem là chưa hợp lệ.
        if planned_minutes <= 0:
            continue

        actual_hours = (
            D((checkout - checkin).total_seconds())
            / D(3600)
        )

        # Giờ chuẩn tối đa bằng thời lượng ca.
        # Phần vượt ca chưa được tính thành OT.
        standard_hours = min(
            actual_hours,
            D(planned_minutes) / D(60)
        )

        employee_id = record.ma_lich_lam.ma_nv_id

        # Cộng dồn tất cả ca đã checkout trong tháng.
        time_map[employee_id] = (
            time_map.get(employee_id, D(0))
            + standard_hours
        )

    # ==========================================
    # 5. KIỂM TRA YÊU CẦU ĐIỀU CHỈNH CÔNG
    # ==========================================
    pending = set(
        YeuCauDieuChinhCong.objects
        .filter(
            ma_lich_lam__ngay_lam__range=(
                start,
                end
            ),
            trang_thai="Cho_duyet"
        )
        .values_list(
            "ma_lich_lam__ma_nv_id",
            flat=True
        )
    )

    # ==========================================
    # 6. TÍNH LƯƠNG TỪNG NHÂN VIÊN
    # ==========================================
    rows = []

    for nv in employees:

        contract = contract_map.get(nv.pk)
        cfg = config_map.get(nv.pk)

        hours = time_map.get(
            nv.pk,
            D(0)
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP
        )

        issues = []

        if nv.pk in pending:
            issues.append(
                "Có yêu cầu điều chỉnh công đang chờ duyệt"
            )

        if not contract:
            issues.append(
                "Chưa có hợp đồng hiệu lực phù hợp kỳ lương"
            )

        # ======================================
        # 7. XÁC ĐỊNH ĐƠN GIÁ GIỜ TỪ HỢP ĐỒNG
        # ======================================
        rate = D(0)

        if contract:

            if contract.hinh_thuc_luong == "theo_gio":

                # Lấy trực tiếp mức lương theo giờ.
                # Không cần CauHinhLuong.
                rate = D(contract.muc_luong)

            elif contract.hinh_thuc_luong == "theo_thang":

                # Lương tháng cần số giờ chuẩn
                # để quy đổi sang đơn giá giờ.
                if (
                    cfg
                    and cfg.gio_chuan_thang
                    and cfg.gio_chuan_thang > 0
                ):

                    rate = (
                        D(contract.muc_luong)
                        / D(cfg.gio_chuan_thang)
                    ).quantize(
                        CENT,
                        rounding=ROUND_HALF_UP
                    )

                else:
                    issues.append(
                        "Lương tháng thiếu giờ chuẩn để quy đổi"
                    )

            else:
                issues.append(
                    "Hình thức trả lương không hợp lệ"
                )

            if D(contract.muc_luong) <= 0:
                issues.append(
                    "Mức lương trong hợp đồng chưa hợp lệ"
                )

        # ======================================
        # 8. PHỤ CẤP THEO HỢP ĐỒNG
        # ======================================
        allowance = (
            allowance_by_contract.get(
                contract.pk,
                D(0)
            )
            if contract
            else D(0)
        )

        # ======================================
        # 9. KHẤU TRỪ BỔ SUNG
        # ======================================
        # Không có cấu hình thì mặc định
        # không có khấu trừ bổ sung.
        deduction = (
            D(cfg.khau_tru)
            if cfg
            else D(0)
        )

        # ======================================
        # 10. TÍNH LƯƠNG
        # ======================================
        main = (
            rate * hours
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP
        )

        # Chưa có nghiệp vụ OT được duyệt.
        overtime = D(0)
        ot_hours = D(0)

        net = (
            main
            + overtime
            + allowance
            - deduction
        )

        if net < 0:
            issues.append(
                "Khấu trừ vượt thu nhập"
            )

        # ======================================
        # 11. TRẢ DỮ LIỆU CHO PAYROLL
        # ======================================
        rows.append({
            "id": nv.pk,
            "name": nv.ho_ten,
            "position": nv.vi_tri or "",
            "regular": float(hours),
            "ot": float(ot_hours),
            "rate": float(rate),
            "ot_factor": (
                float(cfg.he_so_ot)
                if cfg and cfg.he_so_ot is not None
                else 0
            ),
            "main": float(main),
            "overtime": float(overtime),
            "allowance": float(allowance),
            "deduct": float(deduction),
            "net": float(net),
            "ready": not issues,
            "issues": issues,
        })

    return rows