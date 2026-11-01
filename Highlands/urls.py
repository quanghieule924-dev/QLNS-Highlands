
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render


def home(request):
    return render(request, 'home.html')


def internal_preview(request):
    # Trang xem thử giao diện quản lý (Admin)
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
    # Trang xem thử giao diện nhân viên
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

    # Trang hợp đồng
    path('contracts/', include('contracts.urls')),
]

