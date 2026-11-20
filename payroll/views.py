"""Real database-backed payroll workflow with role checks and CSRF-protected writes."""
import json
from datetime import date
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache
from .models import KyLuong, PhieuLuong
from .services import preview


def is_manager(user):
    return user.is_superuser or getattr(user, 'role', None) == 'admin'


def parse_period(raw):
    try:
        value = date.fromisoformat(str(raw) + '-01')
    except (ValueError, TypeError):
        return None
    return value


def serialize_slip(s):
    return dict(id=s.nhan_vien_id, name=s.nhan_vien.ho_ten, position=s.nhan_vien.vi_tri or '',
        regular=float(s.gio_chuan), ot=float(s.gio_ot), rate=float(s.don_gia_gio),
        main=float(s.luong_chinh), overtime=float(s.luong_ot), allowance=float(s.phu_cap),
        deduct=float(s.khau_tru), net=float(s.thuc_nhan), issued=s.da_phat_hanh,
        paid=s.da_chi_tra, feedback=s.phan_hoi, paidDate=s.ngay_chi_tra.isoformat() if s.ngay_chi_tra else '',
        method=s.phuong_thuc, reference=s.ma_tham_chieu, ready=True, issues=[])


def period_payload(period):
    ky = KyLuong.objects.filter(thang=period).first()
    if ky and ky.da_chot:
        return {'locked': True, 'rows': [serialize_slip(s) for s in PhieuLuong.objects.filter(ky_luong=ky).select_related('nhan_vien').order_by('nhan_vien_id')]}
    return {'locked': False, 'rows': preview(period)}


@login_required
def salary_management(request):
    if not is_manager(request.user):
        raise PermissionDenied('Chỉ quản lý được truy cập quản lý lương.')
    return render(request, 'payroll/management.html', {'role': 'admin', 'active_menu': 'payroll'})


@login_required
def my_payslip(request):
    if getattr(request.user, 'role', None) != 'employee' and not request.user.is_superuser:
        raise PermissionDenied('Phiếu lương chỉ dành cho nhân viên.')
    return render(request, 'payroll/my_payslip.html', {'role': 'employee', 'active_menu': 'payroll'})


@login_required
@never_cache
@require_GET
def payroll_data(request):
    if not is_manager(request.user):
        return JsonResponse({'error': 'Không có quyền.'}, status=403)
    period = parse_period(request.GET.get('period'))
    if not period:
        return JsonResponse({'error': 'Kỳ lương không hợp lệ.'}, status=400)
    return JsonResponse(period_payload(period))


@login_required
@require_POST
def payroll_action(request):
    if not is_manager(request.user):
        return JsonResponse({'error': 'Không có quyền.'}, status=403)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'JSON không hợp lệ.'}, status=400)
    period = parse_period(data.get('period'))
    action = data.get('action')
    if not period or action not in ('lock', 'issue', 'pay'):
        return JsonResponse({'error': 'Tham số không hợp lệ.'}, status=400)
    if period >= date.today().replace(day=1):
        return JsonResponse({'error': 'Chỉ cho phép chốt hoặc chi trả kỳ lương đã kết thúc.'}, status=400)
    try:
        with transaction.atomic():
            ky, _ = KyLuong.objects.select_for_update().get_or_create(thang=period)
            if action == 'lock':
                if ky.da_chot:
                    return JsonResponse({'error': 'Kỳ này đã chốt.'}, status=409)
                rows = preview(period)
                if not rows:
                    return JsonResponse({'error': 'Chưa có nhân viên để lập bảng lương.'}, status=400)
                bad = [r['id'] for r in rows if not r['ready']]
                if bad:
                    return JsonResponse({'error': 'Chưa đủ điều kiện chốt: ' + ', '.join(bad[:12]) + '. Kiểm tra hợp đồng, cấu hình lương và điều chỉnh công.'}, status=400)
                for r in rows:
                    PhieuLuong.objects.create(ky_luong=ky, nhan_vien_id=r['id'], gio_chuan=Decimal(str(r['regular'])), gio_ot=Decimal(str(r['ot'])),
                        don_gia_gio=Decimal(str(r['rate'])), he_so_ot=Decimal(str(r['ot_factor'])),
                        luong_chinh=Decimal(str(r['main'])), luong_ot=Decimal(str(r['overtime'])),
                        phu_cap=Decimal(str(r['allowance'])), khau_tru=Decimal(str(r['deduct'])), thuc_nhan=Decimal(str(r['net'])))
                ky.da_chot, ky.ngay_chot, ky.nguoi_chot = True, timezone.now(), request.user
                ky.save(update_fields=['da_chot','ngay_chot','nguoi_chot'])
            else:
                if not ky.da_chot:
                    return JsonResponse({'error': 'Phải chốt công trước.'}, status=400)
                ids = data.get('ids')
                if not isinstance(ids, list) or not ids or len(ids) > 500 or not all(isinstance(i, str) for i in ids):
                    return JsonResponse({'error': 'Vui lòng chọn phiếu hợp lệ.'}, status=400)
                slips = list(PhieuLuong.objects.select_for_update().filter(ky_luong=ky, nhan_vien_id__in=set(ids)))
                if len(slips) != len(set(ids)):
                    return JsonResponse({'error': 'Có phiếu không tồn tại trong kỳ.'}, status=400)
                if action == 'issue':
                    if any(s.da_phat_hanh for s in slips):
                        return JsonResponse({'error': 'Có phiếu đã phát hành.'}, status=409)
                    for s in slips:
                        s.da_phat_hanh, s.ngay_phat_hanh = True, timezone.now()
                        s.save(update_fields=['da_phat_hanh','ngay_phat_hanh'])
                else:
                    method = data.get('method')
                    paid_date = date.fromisoformat(data.get('paidDate', '')) if data.get('paidDate') else None
                    ref = str(data.get('reference', ''))[:100]
                    if method not in ('Chuyển khoản','Tiền mặt') or not paid_date or paid_date > date.today():
                        return JsonResponse({'error': 'Thông tin chi trả không hợp lệ.'}, status=400)
                    if any((not s.da_phat_hanh) or s.da_chi_tra for s in slips):
                        return JsonResponse({'error': 'Chỉ ghi nhận phiếu đã phát hành, chưa chi trả.'}, status=409)
                    for s in slips:
                        s.da_chi_tra, s.ngay_chi_tra, s.phuong_thuc, s.ma_tham_chieu = True, paid_date, method, ref
                        s.save(update_fields=['da_chi_tra','ngay_chi_tra','phuong_thuc','ma_tham_chieu'])
    except ValueError:
        return JsonResponse({'error': 'Ngày chi trả không hợp lệ.'}, status=400)
    return JsonResponse({'ok': True, **period_payload(period)})


@login_required
@require_GET
def employee_data(request):
    nv = getattr(request.user, 'nhan_vien', None)
    if not nv:
        return JsonResponse({'rows': [], 'employee': None})
    slips = PhieuLuong.objects.filter(nhan_vien=nv, da_phat_hanh=True).select_related('nhan_vien', 'ky_luong').order_by('-ky_luong__thang')
    return JsonResponse({'employee': {'id': nv.pk, 'name': nv.ho_ten, 'position': nv.vi_tri or ''},
        'rows': [{**serialize_slip(s), 'period': s.ky_luong.thang.strftime('%Y-%m')} for s in slips]})


@login_required
@require_POST
def employee_feedback(request):
    nv = getattr(request.user, 'nhan_vien', None)
    if not nv or getattr(request.user, 'role', None) != 'employee':
        return JsonResponse({'error': 'Không có quyền.'}, status=403)
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'JSON không hợp lệ.'}, status=400)
    period = parse_period(data.get('period'))
    kind = data.get('feedback')
    if not period or kind not in ('received', 'issue'):
        return JsonResponse({'error': 'Phản hồi không hợp lệ.'}, status=400)
    with transaction.atomic():
        slip = PhieuLuong.objects.select_for_update().filter(ky_luong__thang=period, nhan_vien=nv, da_phat_hanh=True, da_chi_tra=True).first()
        if not slip or slip.phan_hoi != 'none':
            return JsonResponse({'error': 'Phiếu chưa chi trả hoặc đã phản hồi.'}, status=409)
        slip.phan_hoi, slip.ngay_phan_hoi = kind, timezone.now()
        slip.save(update_fields=['phan_hoi','ngay_phan_hoi'])
    return JsonResponse({'ok': True})
