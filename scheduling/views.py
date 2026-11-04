
"""Highlands HRM: đăng ký ca, phân ca, lịch sử và công bố lịch."""
import datetime
import unicodedata
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_http_methods

from employees.models import NhanVien
from .models import (
    CaLamViec, DangKyCa, DotDangKy, LichLamViec,
    LuotNopDangKy, YeuCauDoiCa, DinhBienCa,
)

# Không đổi tên role trong accounts: 'admin' là Quản lý; 'employee' là Nhân viên.
VI_TRI = [
    ('Trưởng ca', 'truongca'),
    ('Thu ngân', 'thungan'),
    ('Pha chế', 'phache'),
    ('Phục vụ', 'phucvu'),
]


def chuan_hoa_vi_tri(value):
    value = unicodedata.normalize('NFD', (value or '').strip().lower())
    value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
    value = value.replace('đ', 'd')
    value = ''.join(c for c in value if c.isalnum())
    return {
        'truongca': 'truongca', 'quanlyca': 'truongca',
        'thungan': 'thungan', 'phache': 'phache',
        'barista': 'phache', 'phucvu': 'phucvu',
    }.get(value, '')


def ngay_trong_tuan(dot):
    # Toàn bộ tuần: thứ Hai đến Chủ nhật (7 ngày).
    return [dot.ngay_bat_dau_tuan + datetime.timedelta(days=i) for i in range(7)] if dot else []


def co_the_dang_ky(dot):
    return bool(dot and dot.trang_thai == 'Mở form' and timezone.now() < dot.han_nhan_dang_ky)


def link_dot(request, dot):
    return f'{request.path}?dot={dot.pk}'


def lich_su_nop(nv):
    """Một mục cho mỗi đợt; vẫn hiển thị dữ liệu trước khi có bảng LuotNopDangKy."""
    all_submissions = list(
        LuotNopDangKy.objects.filter(ma_nv=nv)
        .select_related('dot_dang_ky').order_by('-dot_dang_ky__ngay_bat_dau_tuan')
    )
    tracked_ids = {sub.dot_dang_ky_id for sub in all_submissions}
    records = []
    for sub in all_submissions:
        items = list(DangKyCa.objects.filter(ma_nv=nv, dot_dang_ky=sub.dot_dang_ky)
                     .select_related('ma_ca_lam').order_by('ngay_lam_dang_ky', 'ma_ca_lam__start_time'))
        records.append({'dot': sub.dot_dang_ky, 'items': items, 'count': len(items),
                        'last_time': sub.cap_nhat_cuoi})

    # Đăng ký dữ liệu cũ chưa được ghi nhận trong bảng lượt nộp.
    old_round_ids = (DangKyCa.objects.filter(ma_nv=nv, dot_dang_ky__isnull=False)
                     .exclude(dot_dang_ky_id__in=tracked_ids)
                     .values_list('dot_dang_ky_id', flat=True).distinct())
    for old_round in DotDangKy.objects.filter(pk__in=old_round_ids):
        items = list(DangKyCa.objects.filter(ma_nv=nv, dot_dang_ky=old_round)
                     .select_related('ma_ca_lam').order_by('ngay_lam_dang_ky', 'ma_ca_lam__start_time'))
        records.append({'dot': old_round, 'items': items, 'count': len(items),
                        'last_time': max((x.thoi_diem_dang_ky for x in items if x.thoi_diem_dang_ky), default=None)})
    records.sort(key=lambda x: x['dot'].ngay_bat_dau_tuan, reverse=True)
    return records


def xu_ly_dang_ky(request, nhan_vien, dot, shifts):
    if not dot:
        messages.error(request, 'Không có đợt đăng ký đang mở.')
        return redirect('scheduling:dashboard')
    danh_sach_ngay = set(ngay_trong_tuan(dot))
    ca_hop_le = {str(c.pk) for c in shifts}
    cap_ngay_ca = set()
    for raw in request.POST.getlist('ca_dang_ky'):
        try:
            raw_ngay, ma_ca = raw.split('|', 1)
            ngay = parse_date(raw_ngay)
        except (ValueError, TypeError):
            messages.error(request, 'Có dữ liệu đăng ký không hợp lệ.')
            return redirect('scheduling:dashboard')
        if ngay not in danh_sach_ngay or ma_ca not in ca_hop_le:
            messages.error(request, 'Ca đăng ký không thuộc đợt đang mở.')
            return redirect('scheduling:dashboard')
        cap_ngay_ca.add((ngay, ma_ca))

    with transaction.atomic():
        dot_khoa = DotDangKy.objects.select_for_update().get(pk=dot.pk)
        if not co_the_dang_ky(dot_khoa):
            messages.error(request, 'Form đã hết hạn hoặc đã đóng. Không thể gửi/chỉnh sửa.')
            return redirect('scheduling:dashboard')
        DangKyCa.objects.filter(ma_nv=nhan_vien, dot_dang_ky=dot_khoa).delete()
        DangKyCa.objects.bulk_create([
            DangKyCa(ma_nv=nhan_vien, dot_dang_ky=dot_khoa,
                      ngay_lam_dang_ky=ngay, ma_ca_lam_id=ma_ca)
            for ngay, ma_ca in sorted(cap_ngay_ca)
        ])
        luot, da_ton_tai = LuotNopDangKy.objects.get_or_create(
            ma_nv=nhan_vien, dot_dang_ky=dot_khoa, defaults={'da_nop': True}
        )
        if da_ton_tai:
            luot.da_nop = True
            luot.save(update_fields=['da_nop', 'cap_nhat_cuoi'])
    messages.success(request, 'Đã lưu đăng ký ca mới nhất thành công!')
    return redirect('scheduling:dashboard')


def xu_ly_mo_dot(request):
    start = parse_date(request.POST.get('start', ''))
    end = parse_date(request.POST.get('end', ''))
    deadline = parse_datetime(request.POST.get('deadline', ''))
    if deadline and timezone.is_naive(deadline):
        deadline = timezone.make_aware(deadline, timezone.get_current_timezone())
    if not start or not end or start.weekday() != 0 or end != start + datetime.timedelta(days=6) or not deadline:
        messages.error(request, 'Tuần phải từ thứ Hai đến Chủ nhật và hạn chót phải hợp lệ.')
        return redirect('scheduling:dashboard')
    if deadline <= timezone.now() or deadline.date() >= start:
        messages.error(request, 'Hạn đăng ký phải nằm trong tương lai và trước tuần làm việc.')
        return redirect('scheduling:dashboard')
    if DotDangKy.objects.filter(ngay_bat_dau_tuan=start).exists():
        messages.error(request, 'Tuần này đã có đợt đăng ký. Vui lòng xem lịch sử.')
        return redirect('scheduling:dashboard')
    dot = DotDangKy.objects.create(
        ten_dot=request.POST.get('name', '').strip() or f'Đăng ký tuần {start.isocalendar().week}',
        ngay_bat_dau_tuan=start, ngay_ket_thuc_tuan=end,
        han_nhan_dang_ky=deadline, trang_thai='Mở form'
    )
    messages.success(request, 'Đã tạo và mở đợt đăng ký mới.')
    return redirect(link_dot(request, dot))



def xu_ly_dinh_bien(request, dot, shifts):
    """Lưu định biên theo ca/vị trí. Có thể cập nhật trước khi công bố."""
    if dot is None:
        messages.error(request, 'Hãy chọn một đợt trước khi thiết lập định biên.')
        return redirect('scheduling:dashboard')
    role_set = {code for _, code in VI_TRI}
    valid_shift_ids = {str(c.pk) for c in shifts}
    valid_items = {}
    for field, value in request.POST.items():
        if not field.startswith('need|'):
            continue
        parts = field.split('|')
        if len(parts) != 3 or parts[1] not in valid_shift_ids or parts[2] not in role_set:
            messages.error(request, 'Ô định biên không hợp lệ.')
            return redirect(link_dot(request, dot))
        try:
            count = int(value)
        except (TypeError, ValueError):
            messages.error(request, 'Số lượng nhân sự phải là số nguyên.')
            return redirect(link_dot(request, dot))
        if count < 0 or count > 30:
            messages.error(request, 'Mỗi vị trí/ca cần số người từ 0 đến 30.')
            return redirect(link_dot(request, dot))
        valid_items[(parts[1], parts[2])] = count
    expected = {(str(c.pk), role) for c in shifts for _, role in VI_TRI}
    if set(valid_items) != expected:
        messages.error(request, 'Biểu mẫu định biên chưa đầy đủ.')
        return redirect(link_dot(request, dot))
    with transaction.atomic():
        locked = DotDangKy.objects.select_for_update().get(pk=dot.pk)
        if locked.trang_thai == 'Đã công bố':
            messages.error(request, 'Không thể đổi định biên của tuần đã công bố.')
            return redirect(link_dot(request, dot))
        for (shift_id, role), count in valid_items.items():
            DinhBienCa.objects.update_or_create(
                dot_dang_ky=locked, ma_ca_lam_id=shift_id, vi_tri=role,
                defaults={'so_luong': count},
            )
    messages.success(request, 'Đã lưu định biên nhân sự cho các ca trong tuần.')
    return redirect(link_dot(request, dot) + '#requirements')


def xu_ly_dong_dang_ky(request, dot):
    """Khóa form đăng ký để danh sách rảnh không thay đổi khi tự động xếp."""
    if dot is None:
        messages.error(request, 'Không tìm thấy đợt đăng ký.')
        return redirect('scheduling:dashboard')
    with transaction.atomic():
        locked = DotDangKy.objects.select_for_update().get(pk=dot.pk)
        if locked.trang_thai == 'Đã công bố':
            messages.error(request, 'Tuần đã công bố.')
        elif locked.trang_thai != 'Đang xếp ca':
            locked.trang_thai = 'Đang xếp ca'
            locked.save(update_fields=['trang_thai'])
            messages.success(request, 'Đã đóng form đăng ký. Có thể xếp ca tự động hoặc thủ công.')
        else:
            messages.info(request, 'Đợt đã đóng form đăng ký.')
    return redirect(link_dot(request, dot))


def ca_trung_gio(shift, other):
    # Dành cho ca trong cùng một ngày; không hỗ trợ ca xuyên nửa đêm.
    return shift.start_time < other.end_time and other.start_time < shift.end_time


def xu_ly_xep_ca_tu_dong(request, dot, shifts):
    """Điền thêm ca NHÁP đến đúng định biên, không xóa phần quản lý xếp tay."""
    if dot is None:
        messages.error(request, 'Chưa có đợt đăng ký.')
        return redirect('scheduling:dashboard')
    days = ngay_trong_tuan(dot)
    roles = {code for _, code in VI_TRI}
    with transaction.atomic():
        locked = DotDangKy.objects.select_for_update().get(pk=dot.pk)
        if locked.trang_thai != 'Đang xếp ca':
            messages.error(request, 'Hãy đóng form đăng ký trước khi tự động xếp ca.')
            return redirect(link_dot(request, dot))
        demands = {(d.ma_ca_lam_id, d.vi_tri): d.so_luong for d in
                   DinhBienCa.objects.filter(dot_dang_ky=locked)}
        if not demands or not any(v > 0 for v in demands.values()):
            messages.error(request, 'Hãy thiết lập và lưu định biên lớn hơn 0 trước khi xếp tự động.')
            return redirect(link_dot(request, dot) + '#requirements')

        employees = list(NhanVien.objects.all().order_by('pk'))
        emap = {nv.pk: nv for nv in employees}
        availability = defaultdict(set)
        for nv_id, day, shift_id in (DangKyCa.objects.filter(dot_dang_ky=locked)
                .values_list('ma_nv_id', 'ngay_lam_dang_ky', 'ma_ca_lam_id')):
            availability[(day, shift_id)].add(nv_id)

        # Đếm cả lịch khác đợt trong cùng tuần để ngăn xếp trùng giờ/chia công bằng.
        current = list(LichLamViec.objects.select_for_update()
                       .filter(ngay_lam__range=[days[0], days[-1]])
                       .select_related('ma_ca_lam'))
        in_cell = defaultdict(set)
        assigned_day = defaultdict(list)
        weekly_load = defaultdict(int)
        for item in current:
            weekly_load[item.ma_nv_id] += 1
            assigned_day[(item.ma_nv_id, item.ngay_lam)].append(item.ma_ca_lam)
            if item.dot_dang_ky_id == locked.pk:
                role = chuan_hoa_vi_tri(emap[item.ma_nv_id].vi_tri) if item.ma_nv_id in emap else ''
                in_cell[(item.ngay_lam, item.ma_ca_lam_id, role)].add(item.ma_nv_id)

        new_rows = []
        missing = []
        for day in days:
            for shift in shifts:
                for label, role in VI_TRI:
                    target = demands.get((shift.pk, role), 0)
                    key = (day, shift.pk, role)
                    need = max(0, target - len(in_cell[key]))
                    if not need:
                        continue
                    pool = []
                    for nv_id in availability[(day, shift.pk)]:
                        nv = emap.get(nv_id)
                        if (nv is None or chuan_hoa_vi_tri(nv.vi_tri) != role
                            or nv_id in in_cell[key]):
                            continue
                        if any(ca_trung_gio(shift, other)
                               for other in assigned_day[(nv_id, day)]):
                            continue
                        pool.append(nv)
                    # Ít ca trước, sau đó cố định theo mã nhân viên để kết quả ổn định.
                    pool.sort(key=lambda nv: (weekly_load[nv.pk], str(nv.pk)))
                    for nv in pool[:need]:
                        new_rows.append(LichLamViec(
                            ma_nv=nv, ma_ca_lam=shift, ngay_lam=day,
                            dot_dang_ky=locked, is_published=False,
                        ))
                        in_cell[key].add(nv.pk)
                        weekly_load[nv.pk] += 1
                        assigned_day[(nv.pk, day)].append(shift)
                    shortfall = target - len(in_cell[key])
                    if shortfall > 0:
                        missing.append((day, shift.ten_ca, label, shortfall))
        LichLamViec.objects.bulk_create(new_rows)

    messages.success(request, f'Đã tự động bổ sung {len(new_rows)} lượt phân ca vào bản nháp. Lịch chưa công bố.')
    if missing:
        details = '; '.join(f'{d:%d/%m} {ca} - {role}: thiếu {n}' for d, ca, role, n in missing[:8])
        if len(missing) > 8:
            details += f'; và {len(missing) - 8} ô khác'
        messages.warning(request, f'Chưa đủ người ở {len(missing)} ô: {details}. Hãy rà soát trước khi công bố.')
    return redirect(link_dot(request, dot))


def xu_ly_phan_ca(request, dot, shifts):
    if dot is None:
        messages.error(request, 'Không có đợt để xếp ca.')
        return redirect('scheduling:dashboard')
    if dot.trang_thai == 'Đã công bố':
        messages.error(request, 'Lịch đã công bố chỉ được xem, không thể sửa trực tiếp.')
        return redirect(link_dot(request, dot))

    if dot.trang_thai != 'Đang xếp ca':
        messages.error(request, 'Hãy đóng form đăng ký trước khi lưu hoặc công bố phân ca.')
        return redirect(link_dot(request, dot))

    nv_by_id = {str(nv.pk): nv for nv in NhanVien.objects.all()}
    shift_by_id = {str(c.pk): c for c in shifts}
    reg = set(DangKyCa.objects.filter(dot_dang_ky=dot)
              .values_list('ma_nv_id', 'ngay_lam_dang_ky', 'ma_ca_lam_id'))
    days = set(ngay_trong_tuan(dot))
    valid_roles = {x[1] for x in VI_TRI}
    wanted = set()
    assigned_time = defaultdict(list)

    for key in request.POST:
        if not key.startswith('pick|'):
            continue
        try:
            _, raw_ngay, shift_id, role_id = key.split('|', 3)
            ngay = parse_date(raw_ngay)
        except (ValueError, TypeError):
            messages.error(request, 'Dữ liệu ô phân ca không hợp lệ.')
            return redirect(link_dot(request, dot))
        shift = shift_by_id.get(shift_id)
        if ngay not in days or not shift or role_id not in valid_roles:
            messages.error(request, 'Ngày, ca hoặc vị trí không hợp lệ.')
            return redirect(link_dot(request, dot))
        for nv_id in request.POST.getlist(key):
            nv = nv_by_id.get(nv_id)
            if not nv or chuan_hoa_vi_tri(nv.vi_tri) != role_id or (nv.pk, ngay, shift.pk) not in reg:
                messages.error(request, 'Chỉ được chọn nhân viên đúng vị trí, đã đăng ký ca đó.')
                return redirect(link_dot(request, dot))
            marker = (nv.pk, ngay, shift.pk)
            if marker in wanted:
                continue
            if any(shift.start_time < other.end_time and other.start_time < shift.end_time
                   for other in assigned_time[(nv.pk, ngay)]):
                messages.error(request, f'{nv.ho_ten} bị xếp trùng giờ trong ngày {ngay:%d/%m}.')
                return redirect(link_dot(request, dot))
            assigned_time[(nv.pk, ngay)].append(shift)
            wanted.add(marker)

    # Chặn lịch ở đợt khác trùng giờ với lịch quản lý đang xếp.
    other_schedules = LichLamViec.objects.filter(ngay_lam__in=days).exclude(dot_dang_ky=dot).select_related('ma_ca_lam')
    for item in other_schedules:
        if any(nv_id == item.ma_nv_id and ngay == item.ngay_lam and
               ca_trung_gio(shift_by_id[str(ca_id)], item.ma_ca_lam)
               for nv_id, ngay, ca_id in wanted):
            messages.error(request, f'{item.ma_nv}: có ca trùng ở đợt khác ngày {item.ngay_lam:%d/%m}.')
            return redirect(link_dot(request, dot))

    # Một bản ghi LichLamViec tương ứng MỘT người + MỘT ngày + MỘT ca.
    # Không xóa lịch đã liên kết chấm công hoặc yêu cầu đổi ca.
    with transaction.atomic():
        locked = DotDangKy.objects.select_for_update().get(pk=dot.pk)
        if locked.trang_thai != 'Đang xếp ca':
            messages.error(request, 'Trạng thái đợt đã thay đổi, vui lòng tải lại.')
            return redirect(link_dot(request, dot))
        old_rows = list(LichLamViec.objects.select_for_update().filter(dot_dang_ky=locked))
        old_by_key = defaultdict(list)
        for row in old_rows:
            old_by_key[(row.ma_nv_id, row.ngay_lam, row.ma_ca_lam_id)].append(row)
        delete_ids = []
        for marker, rows in old_by_key.items():
            if marker not in wanted:
                delete_ids.extend(r.pk for r in rows)
            else:
                delete_ids.extend(r.pk for r in rows[1:])
        if delete_ids:
            if YeuCauDoiCa.objects.filter(ma_lich_lam_gui_id__in=delete_ids).exists():
                messages.error(request, 'Có lịch đã phát sinh yêu cầu đổi ca; không thể xóa phân công đó.')
                return redirect(link_dot(request, dot))
            if LichLamViec.objects.filter(pk__in=delete_ids, cham_cong_set__isnull=False).exists():
                messages.error(request, 'Có lịch đã chấm công; không thể xóa phân công đó.')
                return redirect(link_dot(request, dot))
            LichLamViec.objects.filter(pk__in=delete_ids).delete()
        new_records = [
            LichLamViec(ma_nv_id=nv_id, ngay_lam=ngay, ma_ca_lam_id=ca_id,
                        dot_dang_ky=locked, is_published=False)
            for nv_id, ngay, ca_id in wanted if (nv_id, ngay, ca_id) not in old_by_key
        ]
        LichLamViec.objects.bulk_create(new_records)
        if request.POST.get('action') == 'publish':
            LichLamViec.objects.filter(dot_dang_ky=locked).update(is_published=True)
            locked.trang_thai = 'Đã công bố'
            locked.save(update_fields=['trang_thai'])

    messages.success(request, 'Đã công bố lịch chính thức.' if request.POST.get('action') == 'publish'
                     else 'Đã lưu bản nháp xếp ca.')
    return redirect(link_dot(request, dot))





# =========================================================
# LỊCH LÀM VIỆC CÁ NHÂN THEO TỪNG TUẦN
# =========================================================


# ==========================================================
# TẠO BẢNG LỊCH LÀM VIỆC CÁ NHÂN THEO TUẦN
# ==========================================================


def tao_lich_ca_nhan_theo_tuan(nhan_vien, ca_lam_viec_list):

    # =====================================================
    # 1. LẤY LỊCH ĐÃ ĐƯỢC CÔNG BỐ CỦA NHÂN VIÊN
    # =====================================================

    lich_da_cong_bo = LichLamViec.objects.filter(
        ma_nv=nhan_vien,
        is_published=True
    ).select_related(
        'ma_ca_lam',
        'dot_dang_ky'
    ).order_by('ngay_lam')

    # =====================================================
    # 2. NHÓM LỊCH THEO TUẦN
    # =====================================================

    du_lieu_tuan = {}

    for lich in lich_da_cong_bo:

        # Xác định ngày thứ Hai đầu tuần
        ngay_thu_hai = lich.ngay_lam - datetime.timedelta(
            days=lich.ngay_lam.weekday()
        )

        if ngay_thu_hai not in du_lieu_tuan:

            du_lieu_tuan[ngay_thu_hai] = {
                'ca_da_xep': set(),
                'ten_dot': None
            }

        # Lưu các ca đã được phân công
        du_lieu_tuan[ngay_thu_hai]['ca_da_xep'].add(
            (lich.ngay_lam, lich.ma_ca_lam_id)
        )

        # Lưu tên đợt đăng ký do quản lý tạo
        if lich.dot_dang_ky:
            du_lieu_tuan[ngay_thu_hai]['ten_dot'] = (
                lich.dot_dang_ky.ten_dot
            )

    # =====================================================
    # 3. TẠO DỮ LIỆU HIỂN THỊ BẢNG LỊCH
    # =====================================================

    ket_qua = []

    # Tuần mới nhất hiển thị trước
    for thu_hai in sorted(du_lieu_tuan, reverse=True):

        chu_nhat = thu_hai + datetime.timedelta(days=6)

        ngay_trong_tuan = [
            thu_hai + datetime.timedelta(days=i)
            for i in range(7)
        ]

        thong_tin = du_lieu_tuan[thu_hai]

        # Tên đợt do quản lý đặt
        ten_dot = thong_tin['ten_dot']

        # Nếu không có tên đợt thì dùng số tuần ISO
        if not ten_dot:
            ten_dot = f"Tuần {thu_hai.isocalendar().week}"

        # =================================================
        # 4. TẠO 3 HÀNG CA SÁNG - CHIỀU - TỐI
        # =================================================

        cac_hang_ca = []

        for ca in ca_lam_viec_list:

            mau_ca = {
                'Ca Sáng': 'ca-sang',
                'Ca Chiều': 'ca-chieu',
                'Ca Tối': 'ca-toi'
            }.get(ca.ten_ca, '')

            cac_ngay = []

            for ngay in ngay_trong_tuan:

                da_xep = (
                    ngay,
                    ca.pk
                ) in thong_tin['ca_da_xep']

                cac_ngay.append({
                    'ngay': ngay,
                    'da_xep': da_xep
                })

            cac_hang_ca.append({
                'ca': ca,
                'mau_ca': mau_ca,
                'cac_ngay': cac_ngay
            })

        # =================================================
        # 5. LƯU THÔNG TIN TUẦN
        # =================================================

        ket_qua.append({
            'ten_dot': ten_dot,
            'nam': thu_hai.year,
            'ngay_bat_dau': thu_hai,
            'ngay_ket_thuc': chu_nhat,
            'ngay_trong_tuan': ngay_trong_tuan,
            'cac_hang_ca': cac_hang_ca
        })

    return ket_qua


@login_required
@require_http_methods(['GET', 'POST'])

def scheduling_dashboard(request):
    user = request.user
    shifts = list(CaLamViec.objects.all().order_by('start_time', 'pk'))
    rounds = DotDangKy.objects.order_by('-ngay_bat_dau_tuan', '-pk')

    if user.role == 'employee':
        nhan_vien = NhanVien.objects.filter(tai_khoan=user).first()
        if nhan_vien is None:
            messages.error(request, 'Tài khoản của bạn chưa được liên kết với hồ sơ nhân viên.')
            return redirect('accounts:dashboard')
        dot = rounds.filter(trang_thai='Mở form', han_nhan_dang_ky__gt=timezone.now()).first()
        if request.method == 'POST':
            if request.POST.get('action') != 'save_registration':
                messages.error(request, 'Yêu cầu không hợp lệ.')
                return redirect('scheduling:dashboard')
            return xu_ly_dang_ky(request, nhan_vien, dot, shifts)
        submitted = False
        selected = set()
        if dot:
            submitted = LuotNopDangKy.objects.filter(ma_nv=nhan_vien, dot_dang_ky=dot).exists()
            selected = set(DangKyCa.objects.filter(ma_nv=nhan_vien, dot_dang_ky=dot)
                           .values_list('ngay_lam_dang_ky', 'ma_ca_lam_id'))
            submitted = submitted or bool(selected)  # Dữ liệu cũ trước khi có LuotNopDangKy
        cards = [{'date': d, 'shifts': [
            {'obj': ca, 'checked': (d, ca.pk) in selected} for ca in shifts
        ]} for d in ngay_trong_tuan(dot)]
        return render(request, 'scheduling/dashboard.html', {
            'active_menu': 'scheduling', 'dot': dot, 'submitted': submitted,
            'can_edit': co_the_dang_ky(dot), 'days': cards,
            'history': lich_su_nop(nhan_vien),
            'official': LichLamViec.objects.filter(ma_nv=nhan_vien, is_published=True)
                        .select_related('ma_ca_lam', 'dot_dang_ky').order_by('-ngay_lam'),
            'official_weeks': tao_lich_ca_nhan_theo_tuan(nhan_vien, shifts),

        })

    if user.role != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập mục phân ca.')
        return redirect('accounts:dashboard')

    chosen = request.GET.get('dot', '')
    dot = rounds.filter(pk=int(chosen)).first() if chosen.isdigit() else rounds.first()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_round':
            return xu_ly_mo_dot(request)
        if action == 'save_requirements':
            return xu_ly_dinh_bien(request, dot, shifts)
        if action == 'close_registration':
            return xu_ly_dong_dang_ky(request, dot)
        if action == 'auto_assign':
            return xu_ly_xep_ca_tu_dong(request, dot, shifts)
        if action in ('save_draft', 'publish'):
            return xu_ly_phan_ca(request, dot, shifts)
        messages.error(request, 'Yêu cầu không hợp lệ.')
        return redirect('scheduling:dashboard')

    matrix = []
    needs = {}
    requirement_rows = []
    if dot:
        needs = {(x.ma_ca_lam_id, x.vi_tri): x.so_luong for x in DinhBienCa.objects.filter(dot_dang_ky=dot)}
        requirement_rows = [
            {'shift': shift, 'roles': [
                {'label': label, 'code': code, 'count': needs.get((shift.pk, code), 0)}
                for label, code in VI_TRI
            ]} for shift in shifts
        ]
        employees = list(NhanVien.objects.all().order_by('ho_ten'))
        emap = {e.pk: e for e in employees}
        assigned_records = list(LichLamViec.objects.filter(dot_dang_ky=dot)
                                .select_related('ma_nv', 'ma_ca_lam'))
        assigned = {(r.ma_nv_id, r.ngay_lam, r.ma_ca_lam_id) for r in assigned_records}
        regs = DangKyCa.objects.filter(dot_dang_ky=dot).values_list(
            'ma_nv_id', 'ngay_lam_dang_ky', 'ma_ca_lam_id'
        )
        candidate_map = defaultdict(set)
        for nv_id, day, ca_id in regs:
            nv = emap.get(nv_id)
            if nv:
                candidate_map[(day, ca_id, chuan_hoa_vi_tri(nv.vi_tri))].add(nv_id)
        # Giữ người đã được phân công khi xem lịch cũ, kể cả đăng ký gốc được chỉnh sửa.
        for item in assigned_records:
            candidate_map[(item.ngay_lam, item.ma_ca_lam_id,
                           chuan_hoa_vi_tri(item.ma_nv.vi_tri))].add(item.ma_nv_id)
        for shift in shifts:
            for idx, (label, code) in enumerate(VI_TRI):
                cells = []
                for day in ngay_trong_tuan(dot):
                    ids = candidate_map.get((day, shift.pk, code), set())
                    candidates = [x for x in employees if x.pk in ids]
                    options = [{'nv': nv, 'selected': (nv.pk, day, shift.pk) in assigned}
                               for nv in candidates]
                    selected_names = [r.ma_nv.ho_ten for r in assigned_records
                                      if r.ngay_lam == day and r.ma_ca_lam_id == shift.pk
                                      and chuan_hoa_vi_tri(r.ma_nv.vi_tri) == code]
                    cells.append({'day': day, 'shift': shift, 'role': code,
                                  'options': options, 'selected_names': selected_names,
                                  'count': len(selected_names),
                                  'required': needs.get((shift.pk, code), 0)})
                matrix.append({'shift': shift, 'role_label': label,
                               'first_role': idx == 0, 'cells': cells})

    return render(request, 'scheduling/dashboard.html', {
        'active_menu': 'scheduling', 'dot': dot, 'rounds': list(rounds),
        'matrix': matrix, 'days': ngay_trong_tuan(dot),
        'requirement_rows': requirement_rows, 'requirements_defined': bool(needs),
        'readonly': bool(dot and dot.trang_thai == 'Đã công bố'),
        'can_schedule': bool(dot and dot.trang_thai == 'Đang xếp ca'),
        'registrations': DangKyCa.objects.filter(dot_dang_ky=dot)
                         .select_related('ma_nv', 'ma_ca_lam').order_by('ngay_lam_dang_ky') if dot else [],
        'shifts': shifts,

    })
