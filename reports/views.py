from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
import json


@login_required
def monthly_dashboard(request):
    # Chỉ quản lý được xem
    if not request.user.is_superuser and getattr(request.user, 'role', None) != 'admin':
        raise PermissionDenied("Bạn không có quyền truy cập trang báo cáo thống kê.")

    selected_month = request.GET.get('month', '2026-11')

    # DỮ LIỆU MẪU
    stats = {
        'total_employees': 58,
        'new_employees': 6,
        'resigned_employees': 2,
        'expiring_contracts': 5,
        'on_time_rate': 93,
        'total_ot_hours': 126,
    }

    chart_data = {
        'department_labels': ['Pha chế', 'Phục vụ', 'Thu ngân', 'Kho', 'Quản lý'],
        'department_values': [16, 18, 10, 6, 8],

        'gender_labels': ['Nam', 'Nữ'],
        'gender_values': [22, 36],

        'attendance_labels': ['Tuần 1', 'Tuần 2', 'Tuần 3', 'Tuần 4'],
        'attendance_on_time': [92, 94, 90, 95],
        'attendance_late': [8, 6, 10, 5],

        'contract_labels': ['Còn hạn', 'Sắp hết hạn', 'Hết hạn'],
        'contract_values': [46, 8, 4],

        'recruitment_labels': ['Ứng tuyển', 'Phỏng vấn', 'Đạt', 'Nhận việc'],
        'recruitment_values': [24, 12, 8, 6],

        'radar_labels': [
            'Đúng giờ',
            'Chuyên cần',
            'Hoàn thành ca',
            'Duy trì nhân sự',
            'Đào tạo',
            'Tuyển dụng'
        ],
        'radar_values': [93, 88, 90, 84, 76, 72],
    }

    context = {
        'active_menu': 'reports',
        'role': request.user.role,
        'selected_month': selected_month,
        'stats': stats,
        'chart_data': chart_data,
    }
    return render(request, 'reports/monthly_dashboard.html', context)