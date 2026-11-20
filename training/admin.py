from django.contrib import admin
from .models import KhungChuongTrinh, BaiHocKhungMau


class BaiHocKhungMauInline(admin.TabularInline):
    model = BaiHocKhungMau
    extra = 1


@admin.register(KhungChuongTrinh)
class KhungChuongTrinhAdmin(admin.ModelAdmin):
    list_display = ("ma_khung", "ten_khung", "vi_tri")
    search_fields = ("ma_khung", "ten_khung", "vi_tri")
    list_filter = ("vi_tri",)
    inlines = [BaiHocKhungMauInline]
