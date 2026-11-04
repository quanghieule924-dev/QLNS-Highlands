from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.conf import settings
from django.conf.urls.static import static


def home(request):
    return render(request, 'home.html')


def internal_preview(request):
    return render(
        request,
        'internal_preview.html',
        {
            'role': 'admin',
            'active_menu': 'dashboard',
            'preview_mode': True,
        },
    )


def employee_preview(request):
    return render(
        request,
        'employee_preview.html',
        {
            'role': 'employee',
            'active_menu': 'dashboard',
            'preview_mode': True,
        },
    )


urlpatterns = [
    path('admin/', admin.site.urls),

    # Trang công khai
    path('', home, name='home'),

    # Đăng nhập, đăng ký, dashboard, đăng xuất
    path('accounts/', include('accounts.urls')),

    # Kết nối app recruitment
    path('recruitment/', include('recruitment.urls')),

    # Trang xem thử giao diện quản lý
    path(
        'internal-preview/',
        internal_preview,
        name='internal_preview',
    ),

    # Trang xem thử giao diện nhân viên
    path(
        'employee-preview/',
        employee_preview,
        name='employee_preview',
    ),

    # --- TÍCH HỢP ĐẦY ĐỦ TẤT CẢ CÁC APP CỦA NHÓM ---
    # Trang hợp đồng
    path('contracts/', include('contracts.urls')),

    path('payroll/', include('payroll.urls')),
    path('reports/', include('reports.urls')),
    path('scheduling/', include('scheduling.urls', namespace='scheduling')),
    path('attendance/', include('attendance.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)