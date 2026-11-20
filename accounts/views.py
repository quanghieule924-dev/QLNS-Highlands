
from datetime import timedelta
from django.db.models import Q

from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from employees.models import NhanVien
from recruitment.models import HoSoUngTuyen
from contracts.models import HopDong
from scheduling.models import LichLamViec
from attendance.models import DuLieuChamCong, YeuCauDieuChinhCong
from training.models import ChuongTrinhTapSu


# ==========================================
# 1. ĐĂNG NHẬP
# ==========================================

class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user

        # Quản lý hoặc Superuser vào Dashboard quản lý
        if user.is_superuser or getattr(user, 'role', None) == 'admin':
            return reverse_lazy('accounts:dashboard')

        if getattr(user, 'role', None) == 'employee':
            return reverse_lazy('accounts:dashboard')

        # Ứng viên về trang chủ công khai
        return reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Không chọn ghi nhớ: phiên hết hạn khi đóng trình duyệt
        if not self.request.POST.get('remember_me'):
            self.request.session.set_expiry(0)

        return response


# ==========================================
# 2. DASHBOARD TỔNG QUAN QUẢN LÝ
# ==========================================

@login_required
def dashboard(request):
    #print("DEBUG: ĐANG CHẠY DASHBOARD CỦA HIẾU")
    """Hai dashboard theo role; chỉ sử dụng dữ liệu thực, không dựng số giả."""
    user = request.user
    role = 'admin' if user.is_superuser else getattr(user, 'role', None)
    if role not in ('admin', 'employee'):
        raise PermissionDenied('Chỉ tài khoản nội bộ được truy cập tổng quan.')

    today = timezone.localdate()
    context = {
        'role': role,
        'active_menu': 'dashboard',
        'today': today,
    }

    if role == 'admin':
        # Số liệu lấy trực tiếp từ các module dùng chung, không có dữ liệu mẫu.
        expiring_qs = HopDong.objects.select_related('nhan_vien').filter(
            trang_thai_hd='dang_hieu_luc',
            loai_hd='co_thoi_han',
            ngay_ket_thuc__gte=today,
            ngay_ket_thuc__lte=today + timedelta(days=30),
        ).order_by('ngay_ket_thuc')
        month_start = today.replace(day=1)
        context.update({
            'employee_count': NhanVien.objects.count(),
            'application_count': HoSoUngTuyen.objects.count(),
            'contract_count': HopDong.objects.count(),
            'shifts_today': LichLamViec.objects.filter(ngay_lam=today, is_published=True).count(),
            'recent_applications': HoSoUngTuyen.objects.select_related(
                'ma_ung_vien', 'ma_vi_tri'
            ).order_by('-ngay_nop', '-pk')[:5],
            'expiring_contracts': expiring_qs[:5],
            'expiring_contract_count': expiring_qs.count(),
            'attendance_today': DuLieuChamCong.objects.filter(
                ma_lich_lam__ngay_lam=today, time_checkin__isnull=False,
            ).count(),
            'pending_attendance_requests': YeuCauDieuChinhCong.objects.filter(
                trang_thai='Cho_duyet'
            ).count(),
            'new_employees_month': NhanVien.objects.filter(
                ngay_vao_lam__gte=month_start, ngay_vao_lam__lte=today
            ).count(),
            'training_program_count': ChuongTrinhTapSu.objects.count(),
        })
        template = 'accounts/dashboard_manager.html'
    else:
        # Ràng buộc duy nhất bằng khóa OneToOne tai_khoan, không đối chiếu tên/email.
        employee = NhanVien.objects.filter(tai_khoan=user).first()
        context.update({
            'display_name': employee.ho_ten if employee else (user.get_full_name() or user.username),
            'employee_profile_linked': employee is not None,
            'employee': employee,
            'next_shift': None,
            'month_attendance': 0,
            'my_contract': None,
            'my_training': None,
            'recent_shifts': [],
            'payslip_available': False,  # payroll/models.py chưa có model phiếu lương.
        })
        if employee is not None:
            upcoming = LichLamViec.objects.filter(
                ma_nv=employee, ngay_lam__gte=today, is_published=True
            ).select_related('ma_ca_lam').order_by('ngay_lam', 'ma_ca_lam__start_time')
            active_contract = HopDong.objects.filter(
                nhan_vien=employee, trang_thai_hd='dang_hieu_luc',
                ngay_bat_dau__lte=today,
            ).filter(Q(ngay_ket_thuc__isnull=True) | Q(ngay_ket_thuc__gte=today)).order_by('-ngay_bat_dau').first()
            if active_contract is None:
                active_contract = HopDong.objects.filter(nhan_vien=employee).order_by('-ngay_bat_dau').first()
            month_start = today.replace(day=1)
            context.update({
                'next_shift': upcoming.first(),
                'recent_shifts': list(upcoming[:5]),
                'month_attendance': DuLieuChamCong.objects.filter(
                    ma_lich_lam__ma_nv=employee,
                    ma_lich_lam__ngay_lam__range=(month_start, today),
                    time_checkin__isnull=False,
                ).count(),
                'my_contract': active_contract,
                'my_training': ChuongTrinhTapSu.objects.filter(ma_nv=employee).order_by('-pk').first(),
            })
        template = 'accounts/dashboard_employee.html'

    return render(request, template, context)


# ==========================================
# 3. ĐĂNG KÝ TÀI KHOẢN (TRANG TẠM)
# ==========================================

def register_view(request):
    return render(request, 'accounts/register.html')


# ==========================================
# 4. TRANG GIỚI THIỆU
# ==========================================

def about_view(request):
    return render(request, 'about.html')


# ==========================================
# 5. TRANG TRỢ GIÚP
# ==========================================

def help_page(request):
    return render(request, 'accounts/help.html')


# ==========================================
# 6. DANH SÁCH CHỨC NĂNG SIDEBAR
# ==========================================

# Giá trị đầu dành cho Quản lý.
# Giá trị thứ hai dành cho Nhân viên.
# None nghĩa là Nhân viên không có quyền truy cập.

INTERNAL_MODULES = {
    'employees': ('Quản lý nhân viên', 'Hồ sơ của tôi'),
    'recruitment': ('Tuyển dụng', None),
    'contracts': ('Hợp đồng & phúc lợi', 'Hợp đồng & phúc lợi'),
    'scheduling': ('Phân ca làm việc', 'Lịch làm việc'),
    'attendance': ('Chấm công', 'Chấm công'),
    'payroll': ('Quản lý lương', 'Phiếu lương'),
    'training': ('Đào tạo', 'Đào tạo'),
    'reports': ('Báo cáo thống kê', None),
}


# ==========================================
# 7. TRANG CHỨC NĂNG TẠM THỜI
# ==========================================

@login_required
def module_placeholder(request, slug):
    user = request.user

    # Xác định vai trò
    is_manager = (
        user.is_superuser
        or getattr(user, 'role', None) == 'admin'
    )

    is_employee = getattr(user, 'role', None) == 'employee'

    # Ứng viên và các vai trò khác không được vào khu vực nội bộ
    if not is_manager and not is_employee:
        raise PermissionDenied(
            'Bạn không có quyền truy cập khu vực nội bộ.'
        )

    # Kiểm tra chức năng có tồn tại không
    titles = INTERNAL_MODULES.get(slug)

    if titles is None:
        raise Http404('Chức năng không tồn tại.')

    # Lấy tên chức năng theo vai trò
    if is_manager:
        title = titles[0]
        role = 'admin'
    else:
        title = titles[1]
        role = 'employee'

    # Không cho Nhân viên truy cập chức năng của Quản lý
    if title is None:
        raise PermissionDenied(
            'Bạn không có quyền truy cập chức năng này.'
        )

    return render(
        request,
        'accounts/module_placeholder.html',
        {
            'role': role,
            'active_menu': slug,
            'module_title': title,
        }
    )
