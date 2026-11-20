
from django.contrib import admin

from .models import (
    CaLamViec,
    DotDangKy,
    DangKyCa,
    LichLamViec,
    YeuCauDoiCa,
    LuotNopDangKy,
    DinhBienCa,
)

admin.site.register(CaLamViec)
admin.site.register(DotDangKy)
admin.site.register(DangKyCa)
admin.site.register(LichLamViec)
admin.site.register(YeuCauDoiCa)
admin.site.register(LuotNopDangKy)
admin.site.register(DinhBienCa)
