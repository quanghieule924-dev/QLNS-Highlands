
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
        context.update({
            'employee_count': NhanVien.objects.count(),
            'application_count': HoSoUngTuyen.objects.count(),
            'contract_count': HopDong.objects.count(),
            'shifts_today': LichLamViec.objects.filter(ngay_lam=today).count(),
            'recent_applications': HoSoUngTuyen.objects.select_related(
                'ma_ung_vien', 'ma_vi_tri'
            ).order_by('-ngay_nop', '-pk')[:5],
            'expiring_contracts': HopDong.objects.select_related('nhan_vien').filter(
                ngay_ket_thuc__gte=today,
                ngay_ket_thuc__lte=today + timedelta(days=30),
            ).order_by('ngay_ket_thuc')[:5],
        })
        template = 'accounts/dashboard_manager.html'
    else:
        # Chưa có FK giữa accounts.User và employees.NhanVien.
        # Không ghép hồ sơ bằng tên/email vì có thể lộ lịch/phiếu của người khác.
        # Khi nhóm tạo liên kết 1-1 đáng tin cậy, mới lấy dữ liệu cá nhân thật.
        context.update({
            'display_name': user.get_full_name() or user.username,
            'employee_profile_linked': False,
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
