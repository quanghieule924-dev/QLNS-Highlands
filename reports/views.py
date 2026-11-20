"""Monthly HR reporting using existing Highlands models; no demo figures."""
from calendar import monthrange
from collections import Counter
from datetime import date, datetime, timedelta
from statistics import mean

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone

from attendance.models import DuLieuChamCong
from contracts.models import HopDong
from employees.models import NhanVien
from payroll.models import PhieuLuong
from recruitment.models import HoSoUngTuyen, LichPhongVan
from scheduling.models import LichLamViec
from training.models import ChuongTrinhTapSu


INACTIVE_STATUSES = {'đã nghỉ', 'nghỉ việc', 'đã nghỉ việc', 'ngừng làm việc', 'đã thôi việc', 'nghỉ'}
INTERVIEW_STAGES = {'Đã lên lịch', 'Chờ xác nhận', 'Đã phỏng vấn', 'Đạt phỏng vấn', 'Đã nhận việc', 'Đạt'}
PASSED_STAGES = {'Đạt phỏng vấn', 'Đã nhận việc', 'Đạt'}
HIRED_STAGES = {'Đã nhận việc'}


def _period(raw):
    """Only accept YYYY-MM. Invalid input falls back to the current month."""
    today = timezone.localdate()
    try:
        value = datetime.strptime(raw or '', '%Y-%m').date()
        return date(value.year, value.month, 1)
    except (ValueError, TypeError):
        return today.replace(day=1)


def _percent(numerator, denominator):
    return round(100 * numerator / denominator) if denominator else 0


def _week_index(day):
    # Days 1–7, 8–14, 15–21, 22–28, 29–end: none are dropped.
    return min((day - 1) // 7, 4)


def _on_time(record):
    """Respect the attendance module's 5-minute tolerance."""
    if not record.time_checkin:
        return None
    shift = record.ma_lich_lam.ma_ca_lam
    scheduled = timezone.make_aware(
        datetime.combine(record.ma_lich_lam.ngay_lam, shift.start_time),
        timezone.get_current_timezone(),
    )
    actual = record.time_checkin
    if timezone.is_naive(actual):
        actual = timezone.make_aware(actual, timezone.get_current_timezone())
    return (actual - scheduled).total_seconds() <= 5 * 60


@login_required
def monthly_dashboard(request):
    user = request.user
    if not user.is_superuser and getattr(user, 'role', None) != 'admin':
        raise PermissionDenied('Bạn không có quyền truy cập trang báo cáo thống kê.')

    start = _period(request.GET.get('month'))
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    future_end = end + timedelta(days=30)

    all_employees = list(NhanVien.objects.all().only(
        'manv', 'gioi_tinh', 'vi_tri', 'trang_thai', 'ngay_vao_lam'
    ))
    # Employees active at the end of the requested month, excluding explicit leavers.
    active = [e for e in all_employees if
              (e.ngay_vao_lam is None or e.ngay_vao_lam <= end) and
              (e.trang_thai or '').strip().lower() not in INACTIVE_STATUSES]
    new_count = sum(start <= e.ngay_vao_lam <= end for e in all_employees if e.ngay_vao_lam)

    # Contract termination is the only dated termination information in these models.
    terminated = list(HopDong.objects.filter(
        ngay_cham_dut__range=(start, end), trang_thai_hd='da_cham_dut'
    ).values_list('nhan_vien_id', flat=True).distinct())
    resigned_count = len(terminated)

    # Pick at most one latest, signed/active contract per employee; do not count renewals twice.
    contract_qs = (HopDong.objects.filter(ngay_bat_dau__lte=end)
                   .exclude(trang_thai_hd='cho_ky')
                   .order_by('nhan_vien_id', '-ngay_bat_dau', '-mahd'))
    latest = {}
    for contract in contract_qs:
        latest.setdefault(contract.nhan_vien_id, contract)
    contract_values = [0, 0, 0]  # valid, expiring soon, expired/terminated
    expiring_ids = set()
    for contract in latest.values():
        if (contract.trang_thai_hd == 'da_cham_dut' and
                (contract.ngay_cham_dut is None or contract.ngay_cham_dut <= end)):
            contract_values[2] += 1
        elif contract.ngay_ket_thuc is not None and contract.ngay_ket_thuc < end:
            contract_values[2] += 1
        elif (contract.ngay_ket_thuc is not None and
              end <= contract.ngay_ket_thuc <= future_end):
            contract_values[1] += 1
            expiring_ids.add(contract.nhan_vien_id)
        else:
            contract_values[0] += 1

    departments = Counter((e.vi_tri or 'Chưa cập nhật').strip() or 'Chưa cập nhật' for e in active)
    genders = Counter((e.gioi_tinh or '').strip().lower() for e in active)
    male = genders.get('nam', 0)
    female = genders.get('nữ', 0) + genders.get('nu', 0)
    other = len(active) - male - female
    gender_labels = ['Nam', 'Nữ']
    gender_values = [male, female]
    if other:
        gender_labels.append('Khác / chưa cập nhật')
        gender_values.append(other)

    # One published scheduled shift = one expected attendance slot.
    planned = list(LichLamViec.objects.filter(
        ngay_lam__range=(start, end), is_published=True
    ).values('ma_lich_lam', 'ngay_lam'))
    planned_ids = {entry['ma_lich_lam'] for entry in planned}
    attended = list(DuLieuChamCong.objects.filter(
        ma_lich_lam_id__in=planned_ids, time_checkin__isnull=False
    ).select_related('ma_lich_lam__ma_ca_lam')) if planned_ids else []
    week_counts = [0] * 5
    week_late = [0] * 5
    completed = 0
    for record in attended:
        idx = _week_index(record.ma_lich_lam.ngay_lam.day)
        week_counts[idx] += 1
        if not _on_time(record):
            week_late[idx] += 1
        if record.time_checkout and record.time_checkout > record.time_checkin:
            completed += 1
    attendance_count = sum(week_counts)
    late_count = sum(week_late)
    on_time_count = attendance_count - late_count
    on_time_rate = _percent(on_time_count, attendance_count)
    total_planned = len(planned)
    attendance_rate = _percent(attendance_count, total_planned)
    completion_rate = _percent(completed, total_planned)
    week_total = (end.day - 1) // 7 + 1
    labels = [f'Tuần {n + 1}' for n in range(week_total)]
    on_time_by_week = [_percent(week_counts[i] - week_late[i], week_counts[i]) for i in range(week_total)]
    late_by_week = [_percent(week_late[i], week_counts[i]) for i in range(week_total)]

    # Cohort is defined by application date, not lifetime totals.
    applications = list(HoSoUngTuyen.objects.filter(ngay_nop__range=(start, end))
                        .values('ma_ho_so', 'trang_thai'))
    candidate_ids = {row['ma_ho_so'] for row in applications}
    interviews = (LichPhongVan.objects.filter(ma_ho_so_id__in=candidate_ids)
                  .values_list('ma_ho_so_id', flat=True).distinct()) if candidate_ids else []
    interview_ids = set(interviews)
    interviewed = sum(row['ma_ho_so'] in interview_ids or row['trang_thai'] in INTERVIEW_STAGES
                      for row in applications)
    passed = sum(row['trang_thai'] in PASSED_STAGES for row in applications)
    hired = sum(row['trang_thai'] in HIRED_STAGES for row in applications)

    # OT is only counted from recorded payslips. The attendance model has no approved OT field.
    from django.db.models import Sum
    ot_hours = (PhieuLuong.objects.filter(ky_luong__thang=start)
                .aggregate(value=Sum('gio_ot'))['value'])
    has_payroll = PhieuLuong.objects.filter(ky_luong__thang=start).exists()

    progress = list(ChuongTrinhTapSu.objects.values_list('tong_tien_do', flat=True))
    training_rate = round(mean(progress)) if progress else 0
    retention = _percent(len(active), len(active) + resigned_count) if (active or resigned_count) else 0
    recruitment_rate = _percent(hired, len(applications))

    notes = []
    if not planned:
        notes.append('Chưa có lịch làm đã phát hành trong kỳ; các tỷ lệ chấm công đang hiển thị 0%.')
    elif not attendance_count:
        notes.append('Chưa có lượt check-in cho các ca đã phát hành trong kỳ.')
    if not has_payroll:
        notes.append('Chưa có phiếu lương trong kỳ; chưa thể xác nhận tổng giờ OT.')
    if not applications:
        notes.append('Chưa có hồ sơ ứng tuyển nộp trong kỳ.')
    if not progress:
        notes.append('Chưa có chương trình đào tạo để tính tiến độ.')
    notes.append('Nghỉ việc dựa trên ngày chấm dứt hợp đồng; các chỉ số nhân sự lịch sử phụ thuộc trạng thái hồ sơ hiện tại. Nhóm bộ phận dùng trường vị trí.')

    stats = {
        'total_employees': len(active),
        'new_employees': new_count,
        'resigned_employees': resigned_count,
        'expiring_contracts': len(expiring_ids),
        'on_time_rate': on_time_rate,
        'total_ot_hours': float(ot_hours) if ot_hours is not None else '—',
    }
    department_items = sorted(departments.items(), key=lambda row: (-row[1], row[0]))
    chart_data = {
        'department_labels': [item[0] for item in department_items],
        'department_values': [item[1] for item in department_items],
        'gender_labels': gender_labels,
        'gender_values': gender_values,
        'attendance_labels': labels,
        'attendance_on_time': on_time_by_week,
        'attendance_late': late_by_week,
        'contract_labels': ['Còn hạn', 'Sắp hết hạn', 'Hết hạn'],
        'contract_values': contract_values,
        'recruitment_labels': ['Ứng tuyển', 'Phỏng vấn', 'Đạt', 'Nhận việc'],
        'recruitment_values': [len(applications), interviewed, passed, hired],
        'radar_labels': ['Đúng giờ', 'Chuyên cần', 'Hoàn thành ca', 'Duy trì nhân sự', 'Đào tạo', 'Tuyển dụng'],
        'radar_values': [on_time_rate, attendance_rate, completion_rate, retention, training_rate, recruitment_rate],
    }
    return render(request, 'reports/monthly_dashboard.html', {
        'active_menu': 'reports',
        'role': 'admin',
        'selected_month': start.strftime('%Y-%m'),
        'stats': stats,
        'chart_data': chart_data,
        'report_notes': notes,
    })
