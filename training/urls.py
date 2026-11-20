from django.urls import path
from . import views, exam_student, manager_result

app_name = 'training'

urlpatterns = [
    # 1. Hiển thị
    path('dashboard/', views.dashboard_quan_ly_tap_su, name='dashboard_quan_ly_tap_su'),
    path('ket-qua-thi/<int:ma_kq>/', views.ket_qua_thi, name='ket_qua_thi'),

    # 2. Thao tác tác vụ
    path('duyet-lo-trinh/<int:ma_ct>/', views.duyet_lo_trinh, name='duyet_lo_trinh'),
    path('tich-checklist/<str:ma_nv>/', views.cap_nhat_tien_do_ojt, name='cap_nhat_tien_do_ojt'),
    path('bo-tri-thi/<str:ma_nv>/', views.bo_tri_thi, name='bo_tri_thi'),
    path('duyet-chuong-trinh/<str:pk>/',views.duyet_chuong_trinh,name='duyet_chuong_trinh'),
    path('', views.dao_tao, name='dao_tao'),
    path('chinh-sua-chuong-trinh/<str:pk>/',views.chinh_sua_chuong_trinh,name='chinh_sua_chuong_trinh'),
    path('nhan-vien/',views.dao_tao_nhan_vien,name='dao_tao_nhan_vien'),
    path('lich-thi-nhan-vien/',views.lich_thi_nhan_vien,name='lich_thi_nhan_vien'),
    path('lam-bai/<str:ma_lt>/',exam_student.lam_bai_thi,name='lam_bai_thi'),
    path('luu-dap-an/<str:ma_lt>/',exam_student.luu_dap_an_thi,name='luu_dap_an_thi'),
    path('ket-qua-bai-thi/<str:ma_lt>/',exam_student.ket_qua_bai_thi,name='ket_qua_bai_thi'),
    path('trang-thai-ho-so/<str:ma_nv>/',manager_result.trang_thai_ho_so,name='trang_thai_ho_so'),
    path('chuyen-ho-so/<str:ma_nv>/',manager_result.chuyen_ho_so_tap_su,name='chuyen_ho_so_tap_su'),
]

