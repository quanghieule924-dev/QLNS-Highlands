"""Giao diện Payroll mẫu; tuyệt đối không chốt công, lưu lương hoặc chi trả trong DB."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render


@login_required
def salary_management(request):
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        raise PermissionDenied('Chỉ Quản lý được truy cập quản lý lương.')
    return render(request, 'payroll/management.html', {
        'role': 'admin', 'active_menu': 'payroll',
    })


@login_required
def my_payslip(request):
    if getattr(request.user, 'role', None) != 'employee' and not request.user.is_superuser:
        raise PermissionDenied('Phiếu lương cá nhân chỉ dành cho nhân viên.')
    return render(request, 'payroll/my_payslip.html', {
        'role': 'employee', 'active_menu': 'payroll',
    })
