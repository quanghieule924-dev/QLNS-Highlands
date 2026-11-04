from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    path('quan-ly-ho-so/',views.quan_ly_ho_so_nhan_vien,name='quan_ly_ho_so'),
    path('tiep-nhan/<int:pk>/', views.tiep_nhan_ho_so, name='tiep_nhan_ho_so'),
    path('chuyen-dao-tao/<int:pk>/', views.chuyen_sang_dao_tao, name='chuyen_dao_tao'),
    path('chinh-sua-ho-so/<int:pk>/',views.chinh_sua_ho_so_nhan_vien,name='chinh_sua_ho_so'),
    path('tiep-nhan-dao-tao/<int:pk>/',views.tiep_nhan_va_chuyen_dao_tao,name='tiep_nhan_dao_tao'),
    path('ho-so-cua-toi/',views.ho_so_cua_toi,name='ho_so_cua_toi'),
]
