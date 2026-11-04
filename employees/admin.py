from django.contrib import admin
from .models import NhanVien

@admin.register(NhanVien)
class NhanVienAdmin(admin.ModelAdmin):
    list_display = (
        "manv",
        "ho_ten",
        "vi_tri",
        "trang_thai",
        "tai_khoan",
    )

    search_fields = (
        "manv",
        "ho_ten",
        "tai_khoan__username",
    )

    list_filter = (
        "trang_thai",
        "vi_tri",
    )