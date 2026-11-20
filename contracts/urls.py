
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

    #Chấm dứt hợp đồng
    path(
       '<str:mahd>/cham-dut/',
        views.cham_dut_hop_dong,
        name='cham_dut_hop_dong'
    ),

    #Gia hạn hợp đông
    path(
      '<str:mahd>/gia-han/',
      views.gia_han_hop_dong,
      name='gia_han_hop_dong'
    ),

    # Hợp đồng sắp hết hạn
    path(
        'hop-dong-sap-het-han/',
        views.hop_dong_sap_het_han,
        name='hop_dong_sap_het_han'
    ),

    path(
       'thong-bao/<str:matb>/',
        views.mo_thong_bao,
        name='mo_thong_bao'
    ),




    # Nhân viên ký hợp đồng
    path(
        'hop-dong/<str:mahd>/ky/',
        views.ky_hop_dong,
        name='ky_hop_dong'
    ),


    # Quản lý chế độ phúc lợi
    path(
        'phuc-loi/',
        views.danh_sach_che_do_phuc_loi,
        name='danh_sach_che_do_phuc_loi'
    ),

    path(
        'phuc-loi/them/',
        views.them_che_do_phuc_loi,
        name='them_che_do_phuc_loi'
    ),

    path(
        'phuc-loi/<str:mapl>/sua/',
        views.sua_che_do_phuc_loi,
        name='sua_che_do_phuc_loi'
    ),

    # Tổng quan hợp đồng và phúc lợi
    path(
        '',
        views.tong_quan_hop_dong,
        name='tong_quan_hop_dong'
    ),


path(
    'nhan-vien/<str:manv>/thong-tin/',
    views.lay_thong_tin_nhan_vien,
    name='lay_thong_tin_nhan_vien'
),

# Nhân viên xem phúc lợi của mình
path(
    'phuc-loi-cua-toi/',
    views.phuc_loi_cua_toi,
    name='phuc_loi_cua_toi'
),
    ]
