from django.contrib import admin
from .models import CauHinhLuong, KyLuong, PhieuLuong

@admin.register(CauHinhLuong)
class CauHinhLuongAdmin(admin.ModelAdmin):
    list_display = ('nhan_vien', 'gio_chuan_thang', 'he_so_ot', 'khau_tru')
    search_fields = ('nhan_vien__manv', 'nhan_vien__ho_ten')

@admin.register(KyLuong)
class KyLuongAdmin(admin.ModelAdmin):
    list_display = ('thang', 'da_chot', 'ngay_chot', 'nguoi_chot')

@admin.register(PhieuLuong)
class PhieuLuongAdmin(admin.ModelAdmin):
    list_display = ('nhan_vien', 'ky_luong', 'thuc_nhan', 'da_phat_hanh', 'da_chi_tra', 'phan_hoi')
    list_filter = ('ky_luong', 'da_phat_hanh', 'da_chi_tra', 'phan_hoi')
    search_fields = ('nhan_vien__manv', 'nhan_vien__ho_ten')
    readonly_fields = [f.name for f in PhieuLuong._meta.fields]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
