from django.urls import path
from . import views

app_name = 'recruitment'

urlpatterns = [
    # --- PHẦN ỨNG VIÊN (PUBLIC) ---
    path('tong-quan/', views.recruitment_list_view, name='overview'),
    path('', views.recruitment_list_view, name='recruitment_list'),

    # --- PHẦN QUẢN TRỊ (HRM NỘI BỘ) ---
    path('noi-bo/', views.quan_ly_tuyen_dung, name='quan_ly_tuyen_dung'),
    # Thêm các đường dẫn cho 4 chức năng chính
    path('noi-bo/danh-sach-ho-so/', views.hr_danh_sach_ho_so, name='hr_danh_sach_ho_so'),
    path('noi-bo/sang-loc/', views.hr_sang_loc_cv, name='hr_sang_loc_cv'),
    path('noi-bo/lich-phong-van/', views.hr_lich_phong_van, name='hr_lich_phong_van'),
    path('noi-bo/ket-qua/', views.hr_ket_qua_tuyen_dung, name='hr_ket_qua_tuyen_dung'),

    # --- CÁC ĐƯỜNG DẪN ĐỘNG ---
    path('chi-tiet/<str:ma_dot>/', views.chi_tiet_tuyen_dung_view, name='chi_tiet_tuyen_dung'),
    path('nop-ho-so/<str:ma_dot>/', views.nop_ho_so_view, name='nop_ho_so'),
]

