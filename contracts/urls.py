
from django.urls import path
from . import views


app_name = 'contracts'


urlpatterns = [
    # Danh sách hợp đồng
    path(
        'hop-dong/',
        views.danh_sach_hop_dong,
        name='danh_sach_hop_dong'
    ),

    # Thêm hợp đồng
    path(
        'hop-dong/them/',
        views.them_hop_dong,
        name='them_hop_dong'
    ),

    # Chi tiết hợp đồng
    path(
        'hop-dong/<str:mahd>/',
        views.chi_tiet_hop_dong,
        name='chi_tiet_hop_dong'
    ),

    # Chỉnh sửa hợp đồng
    path(
        'hop-dong/<str:mahd>/sua/',
        views.sua_hop_dong,
        name='sua_hop_dong'
    ),

    # Xóa hợp đồng
    path(
        'hop-dong/<str:mahd>/xoa/',
        views.xoa_hop_dong,
        name='xoa_hop_dong'
    ),

    # Hợp đồng sắp hết hạn
    path(
        'hop-dong-sap-het-han/',
        views.hop_dong_sap_het_han,
        name='hop_dong_sap_het_han'
    ),
]
