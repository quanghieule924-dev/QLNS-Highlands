import re
import uuid
import unicodedata
import secrets

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms import modelform_factory
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from recruitment.models import HoSoUngTuyen
from .models import NhanVien, TiepNhanNhanVien
from training.models import KhungChuongTrinh, BaiHocKhungMau, ChuongTrinhTapSu,BaiHoc, TienDoTapSu


@login_required
def tao_ma_nhan_vien():
    ds = NhanVien.objects.all().order_by('-id')
    so_lon_nhat = 0

    for item in ds:
        ma = getattr(item, 'manv', '') or getattr(item, 'ma_nv', '')
        if ma:
            digits = re.sub(r'\D', '', str(ma))
            if digits:
                so_lon_nhat = max(so_lon_nhat, int(digits))
                break

    return f'NV{so_lon_nhat + 1:03d}'


@login_required
def quan_ly_ho_so_nhan_vien(request):
    # Chỉ quản lý được xem danh sách hồ sơ
    if not (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied(
            'Bạn không có quyền quản lý hồ sơ nhân viên.'
        )

    ds_ho_so = TiepNhanNhanVien.objects.select_related(
        'ho_so',
        'ho_so__ma_ung_vien',
        'ho_so__ma_vi_tri',
        'nhan_vien'
    )

    q = request.GET.get('q', '').strip()
    trang_thai = request.GET.get('trang_thai', '').strip()

    # ========================================
    # BỘ LỌC DANH SÁCH HỒ SƠ
    # ========================================

    q = request.GET.get('q', '').strip()
    vi_tri = request.GET.get('vi_tri', '').strip()
    ma_ho_so = request.GET.get('ma_ho_so', '').strip()
    trang_thai = request.GET.get('trang_thai', '').strip()
    ngay_nop = request.GET.get('ngay_nop', '').strip()

    # ==============================================
    # THỐNG KÊ 4 Ô - LẤY TỪ DATABASE
    # Tính trước khi lọc danh sách để số liệu
    # không bị thay đổi theo ô đang chọn.
    # ==============================================

    tat_ca_ho_so = TiepNhanNhanVien.objects.all()

    tong_ho_so = tat_ca_ho_so.count()

    so_cho_tiep_nhan = tat_ca_ho_so.filter(
        trang_thai='CHO_TIEP_NHAN'
    ).count()

    so_da_tao_ho_so = tat_ca_ho_so.filter(
        trang_thai='DA_TAO_HO_SO'
    ).count()

    so_da_chuyen_dao_tao = tat_ca_ho_so.filter(
        trang_thai='DA_CHUYEN_DAO_TAO'
    ).count()

    # 1. Tìm tên, số điện thoại, email
    if q:
        dieu_kien = (
                Q(ho_so__ma_ung_vien__ho_ten__icontains=q)
                | Q(ho_so__ma_ung_vien__email__icontains=q)
        )

        # Tự nhận biết tên trường điện thoại của model ứng viên
        UngVien = HoSoUngTuyen._meta.get_field(
            'ma_ung_vien'
        ).remote_field.model

        ten_cac_truong = {
            field.name for field in UngVien._meta.fields
        }

        if 'sdt' in ten_cac_truong:
            dieu_kien |= Q(
                ho_so__ma_ung_vien__sdt__icontains=q
            )

        elif 'so_dien_thoai' in ten_cac_truong:
            dieu_kien |= Q(
                ho_so__ma_ung_vien__so_dien_thoai__icontains=q
            )

        ds_ho_so = ds_ho_so.filter(dieu_kien)

    # 2. Lọc vị trí
    if vi_tri:
        ds_ho_so = ds_ho_so.filter(
            ho_so__ma_vi_tri_id=vi_tri
        )

    # 3. Tìm mã hồ sơ
    if ma_ho_so:
        ds_ho_so = ds_ho_so.filter(
            ho_so__ma_ho_so__icontains=ma_ho_so
        )

    # 4. Lọc trạng thái
    if trang_thai:
        ds_ho_so = ds_ho_so.filter(
            trang_thai=trang_thai
        )

    # 5. Lọc ngày nộp
    if ngay_nop:
        ds_ho_so = ds_ho_so.filter(
            ho_so__ngay_nop=ngay_nop
        )

    # Lấy danh sách vị trí từ model đang liên kết với hồ sơ
    ViTriModel = HoSoUngTuyen._meta.get_field(
        'ma_vi_tri'
    ).remote_field.model

    ds_vi_tri = ViTriModel.objects.order_by(
        'ten_vi_tri'
    )

    FormClass = tao_form_chinh_sua_ung_vien(request)
    for item in ds_ho_so:
        item.form_chinh_sua = FormClass(
            instance=item.ho_so.ma_ung_vien
        )
    context = {
        'active_menu': 'employees',
        'ds_ho_so': ds_ho_so,
        'q': q,
        'trang_thai': trang_thai,
        'tong_ho_so': TiepNhanNhanVien.objects.count(),
        'cho_tiep_nhan': TiepNhanNhanVien.objects.filter(
            trang_thai='CHO_TIEP_NHAN'
        ).count(),
        'da_tao_ho_so': TiepNhanNhanVien.objects.filter(
            trang_thai='DA_TAO_HO_SO'
        ).count(),
        'da_chuyen_dao_tao': TiepNhanNhanVien.objects.filter(
            trang_thai='DA_CHUYEN_DAO_TAO'
        ).count(),
        'ds_vi_tri': ds_vi_tri,
        'vi_tri': vi_tri,
        'ma_ho_so': ma_ho_so,
        'ngay_nop': ngay_nop,
        'tong_ho_so': tong_ho_so,
        'so_cho_tiep_nhan': so_cho_tiep_nhan,
        'so_da_tao_ho_so': so_da_tao_ho_so,
        'so_da_chuyen_dao_tao': so_da_chuyen_dao_tao,
    }

    return render(
        request,
        'employees/quan_ly_ho_so.html',
        context
    )


@login_required
@require_POST
def tiep_nhan_ho_so(request, pk):
    # Sử dụng chung luồng tiếp nhận đầy đủ:
    # 1. Tạo nhân viên
    # 2. Tạo và liên kết tài khoản
    # 3. Tạo chương trình đào tạo OJT
    # 4. Cập nhật trạng thái hồ sơ
    return tiep_nhan_va_chuyen_dao_tao(request, pk)

@login_required
def chuyen_sang_dao_tao(request, pk):
    if request.method != 'POST':
        return redirect('employees:quan_ly_ho_so')

    tiep_nhan = get_object_or_404(TiepNhanNhanVien, pk=pk)

    if not tiep_nhan.nhan_vien:
        messages.error(request, 'Bạn cần tiếp nhận hồ sơ trước khi chuyển sang đào tạo.')
        return redirect('employees:quan_ly_ho_so')

    tiep_nhan.trang_thai = 'DA_CHUYEN_DAO_TAO'
    tiep_nhan.save()

    # Nếu bạn đã có flow tạo hồ sơ tập sự thì nối ở đây
    # ví dụ:
    # ChuongTrinhTapSu.objects.get_or_create(ma_nv=tiep_nhan.nhan_vien, ...)

    messages.success(
        request,
        f'Đã chuyển {tiep_nhan.nhan_vien.ho_ten} sang module đào tạo.'
    )
    return redirect('employees:quan_ly_ho_so')

def tao_form_chinh_sua_ung_vien(request):
    """
    Tạo form từ model ứng viên thật trong database.
    Chỉ cho sửa các thông tin cá nhân được cho phép.
    """

    UngVien = HoSoUngTuyen._meta.get_field(
        'ma_ung_vien'
    ).remote_field.model

    truong_cho_phep = [
        'ho_ten',
        'ngay_sinh',
        'gioi_tinh',
        'sdt',
        'so_dien_thoai',
        'email',
        'dia_chi',
    ]

    # Chỉ dùng các trường thực sự có trong model.
    fields = [
        f.name
        for f in UngVien._meta.fields
        if f.name in truong_cho_phep
        and f.editable
        and not f.primary_key
    ]

    FormClass = modelform_factory(
        UngVien,
        fields=fields
    )

    for name, field in FormClass.base_fields.items():
        field.widget.attrs.update({
            'class': 'emp-edit-input'
        })

        if name == 'ngay_sinh':
            field.widget = forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'emp-edit-input'
                }
            )

    return FormClass


@login_required
@require_POST
def chinh_sua_ho_so_nhan_vien(request, pk):

    # Chỉ quản lý được phép chỉnh sửa.
    if not (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied(
            'Bạn không có quyền chỉnh sửa hồ sơ.'
        )

    tiep_nhan = get_object_or_404(
        TiepNhanNhanVien.objects.select_related(
            'ho_so__ma_ung_vien'
        ),
        pk=pk
    )

    ung_vien = tiep_nhan.ho_so.ma_ung_vien

    FormClass = tao_form_chinh_sua_ung_vien(request)

    form = FormClass(
        request.POST,
        instance=ung_vien
    )

    if form.is_valid():

        with transaction.atomic():
            form.save()

        messages.success(
            request,
            'Đã lưu thay đổi hồ sơ thành công.'
        )

    else:
        messages.error(
            request,
            'Thông tin không hợp lệ. '
            'Vui lòng kiểm tra các trường đã nhập. '
            + str(form.errors.get_json_data())
        )

    return redirect(
        'employees:quan_ly_ho_so'
    )


def tao_ma_moi(model, field_name, prefix):
    """Tạo mã ngắn, tránh trùng khóa chính."""
    for _ in range(10):
        ma = prefix + uuid.uuid4().hex[:12].upper()

        if not model.objects.filter(
            **{field_name: ma}
        ).exists():
            return ma

    raise ValueError("Không thể tạo mã mới.")


def chuan_hoa_vi_tri(value):
    """Chuẩn hóa tên vị trí để tìm đúng khung OJT."""
    value = unicodedata.normalize(
        'NFD', str(value or '')
    )
    value = ''.join(
        c for c in value
        if unicodedata.category(c) != 'Mn'
    )
    value = value.replace('đ', 'd').replace('Đ', 'D')
    value = re.sub(
        r'\s+', ' ', value
    ).strip().casefold()

    for prefix in ('nhan vien ', 'nv '):
        if value.startswith(prefix):
            value = value[len(prefix):]

    return value


def tim_khung_dao_tao(ten_vi_tri):
    """
    Tìm khung đào tạo theo vị trí,
    không gán cố định nhân viên vào khung nào.
    """
    vi_tri = chuan_hoa_vi_tri(ten_vi_tri)

    if not vi_tri:
        return None

    khung_phu_hop = []

    for khung in KhungChuongTrinh.objects.all():
        vi_tri_khung = chuan_hoa_vi_tri(khung.vi_tri)
        ten_khung = chuan_hoa_vi_tri(khung.ten_khung)

        if vi_tri == vi_tri_khung:
            khung_phu_hop.append((0, khung))

        elif vi_tri_khung and (
            vi_tri in vi_tri_khung
            or vi_tri_khung in vi_tri
        ):
            khung_phu_hop.append((1, khung))

        elif vi_tri in ten_khung:
            khung_phu_hop.append((2, khung))

    if not khung_phu_hop:
        return None

    khung_phu_hop.sort(key=lambda item: item[0])

    # Không tự chọn tùy tiện nếu nhiều khung cùng mức khớp.
    diem_tot_nhat = khung_phu_hop[0][0]

    khung_tot_nhat = [
        khung for diem, khung in khung_phu_hop
        if diem == diem_tot_nhat
    ]

    if len(khung_tot_nhat) != 1:
        raise ValueError(
            'Có nhiều khung đào tạo phù hợp với vị trí '
            f'{ten_vi_tri}. Cần kiểm tra lại cấu hình.'
        )

    return khung_tot_nhat[0]


def cap_tai_khoan_nhan_vien(nhan_vien):
    """
    Tự động cấp tài khoản và liên kết với nhân viên.
    """

    User = get_user_model()

    # Nếu đã có tài khoản thì không tạo trùng
    if nhan_vien.tai_khoan_id:
        return nhan_vien.tai_khoan, None

    # Username dựa theo mã nhân viên
    username = nhan_vien.manv.lower()

    # Tránh liên kết nhầm tài khoản đã tồn tại
    if User.objects.filter(username=username).exists():
        raise ValueError(
            f'Tài khoản {username} đã tồn tại.'
        )

    # Sinh mật khẩu riêng cho từng nhân viên
    mat_khau = secrets.token_urlsafe(18)

    user = User.objects.create_user(
        username=username,
        password=mat_khau,
        email=nhan_vien.email or '',
        role='employee',
        is_active=True
    )

    # Liên kết tài khoản với nhân viên
    nhan_vien.tai_khoan = user
    nhan_vien.save(update_fields=['tai_khoan'])

    return user, mat_khau

@login_required
def tiep_nhan_va_chuyen_dao_tao(request, pk):

    if not (
        request.user.is_superuser
        or getattr(request.user, 'role', None) == 'admin'
    ):
        raise PermissionDenied(
            'Chỉ quản lý được tiếp nhận nhân viên.'
        )

    if request.method != 'POST':
        return redirect('employees:quan_ly_ho_so')

    try:
        with transaction.atomic():

            tiep_nhan = get_object_or_404(
                TiepNhanNhanVien.objects
                .select_for_update()
                .select_related(
                    'ho_so__ma_ung_vien',
                    'ho_so__ma_vi_tri',
                    'nhan_vien'
                ),
                pk=pk
            )

            if (
                tiep_nhan.trang_thai != 'CHO_TIEP_NHAN'
                or tiep_nhan.nhan_vien_id is not None
            ):
                raise ValueError(
                    'Hồ sơ này đã được tiếp nhận trước đó.'
                )

            ho_so = tiep_nhan.ho_so
            ung_vien = ho_so.ma_ung_vien
            vi_tri = ho_so.ma_vi_tri

            if (
                (ho_so.trang_thai or '')
                .strip()
                .casefold() != 'đạt'
            ):
                raise ValueError(
                    'Chỉ tiếp nhận hồ sơ đã đạt phỏng vấn.'
                )

            # 1. Tìm khung chương trình phù hợp
            khung = tim_khung_dao_tao(
                vi_tri.ten_vi_tri
            )

            if khung is None:
                raise ValueError(
                    'Chưa có khung đào tạo cho vị trí: '
                    + vi_tri.ten_vi_tri
                )

            bai_mau = list(
                BaiHocKhungMau.objects.filter(
                    ma_khung=khung
                ).order_by('buoi_hoc', 'ma_bhk')
            )

            if not bai_mau:
                raise ValueError(
                    'Khung đào tạo chưa có bài học mẫu.'
                )

            # 2. Tạo nhân viên từ ứng viên
            nhan_vien = NhanVien.objects.create(
                manv=tao_ma_moi(
                    NhanVien, 'manv', 'NV'
                ),
                ho_ten=ung_vien.ho_ten,
                ngay_sinh=ung_vien.ngay_sinh,
                sdt=ung_vien.sdt,
                email=ung_vien.email,
                gioi_tinh=ung_vien.gioi_tinh,
                dia_chi=ung_vien.dia_chi,
                vi_tri=vi_tri.ten_vi_tri,
                trang_thai='Tập sự',
                ngay_vao_lam=timezone.localdate()
            )

            chuong_trinh = ChuongTrinhTapSu.objects.create(
                ma_ct=tao_ma_moi(
                    ChuongTrinhTapSu, 'ma_ct', 'CT'
                ),
                ma_nv=nhan_vien,
                ma_khung=khung,
                ten_ct=khung.ten_khung,
                trang_thai_duyet='Chờ duyệt',
                tong_tien_do=0
            )

            # 4. Sao chép bài học mẫu sang chương trình
            for index, mau in enumerate(bai_mau, start=1):

                match = re.search(
                    r'\d+', str(mau.buoi_hoc)
                )

                so_buoi = (
                    int(match.group())
                    if match else index
                )

                BaiHoc.objects.create(
                    ma_bh=tao_ma_moi(
                        BaiHoc, 'ma_bh', 'BH'
                    ),
                    ma_ct=chuong_trinh,
                    ten_bh=mau.ten_bai_hoc,
                    loai_bh=mau.hinh_thuc,
                    buoi_hoc=so_buoi,
                    thoi_gian_hoc=mau.thoi_luong
                )

            # 5. Cập nhật trạng thái tiếp nhận
            tiep_nhan.nhan_vien = nhan_vien
            tiep_nhan.trang_thai = 'DA_CHUYEN_DAO_TAO'
            tiep_nhan.nguoi_tiep_nhan = request.user
            tiep_nhan.ngay_tiep_nhan = timezone.localdate()

            tiep_nhan.save(
                update_fields=[
                    'nhan_vien',
                    'trang_thai',
                    'nguoi_tiep_nhan',
                    'ngay_tiep_nhan',
                    'updated_at'
                ]
            )

    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('employees:quan_ly_ho_so')

    messages.success(
        request,
        f'Đã tiếp nhận {nhan_vien.ho_ten} '
        f'({nhan_vien.manv}) và chuyển sang Đào tạo. '
        'Chương trình đang chờ duyệt.'
    )

    return redirect(
        'training:dashboard_quan_ly_tap_su'
    )


@login_required
def ho_so_cua_toi(request):
    # Chỉ tài khoản nhân viên truy cập hồ sơ cá nhân
    if getattr(request.user, 'role', None) != 'employee':
        raise PermissionDenied(
            'Chỉ nhân viên mới được xem hồ sơ cá nhân.'
        )

    # Lấy đúng nhân viên theo tài khoản đang đăng nhập
    nhan_vien = NhanVien.objects.filter(
        tai_khoan=request.user
    ).first()

    if nhan_vien is None:
        return render(
            request,
            'employees/ho_so_cua_toi.html',
            {
                'active_menu': 'employees',
                'nhan_vien': None,
            }
        )

    # Hồ sơ tiếp nhận từ tuyển dụng
    tiep_nhan = (
        TiepNhanNhanVien.objects
        .filter(nhan_vien=nhan_vien)
        .select_related('ho_so')
        .first()
    )

    # Chương trình đào tạo gần nhất
    chuong_trinh = (
        ChuongTrinhTapSu.objects
        .filter(ma_nv=nhan_vien)
        .order_by('-ma_ct')
        .first()
    )

    tong_bai = 0
    so_bai_dat = 0
    tien_do = 0

    if chuong_trinh:
        bai_hoc = BaiHoc.objects.filter(
            ma_ct=chuong_trinh
        )

        tong_bai = bai_hoc.count()

        # Mỗi bài học chỉ tính Đạt một lần
        for bai in bai_hoc:
            danh_gia = (
                TienDoTapSu.objects
                .filter(
                    ma_nv=nhan_vien,
                    ma_bh=bai
                )
                .order_by('-ngay_danh_gia', '-pk')
                .first()
            )

            if (
                danh_gia
                and danh_gia.trang_thai_danh_gia == 'Đạt'
            ):
                so_bai_dat += 1

        if tong_bai > 0:
            tien_do = round(
                so_bai_dat * 100 / tong_bai,
                1
            )

    context = {
        'active_menu': 'employees',
        'nhan_vien': nhan_vien,
        'tiep_nhan': tiep_nhan,
        'chuong_trinh': chuong_trinh,
        'tong_bai': tong_bai,
        'so_bai_dat': so_bai_dat,
        'tien_do': tien_do,
    }

    return render(
        request,
        'employees/ho_so_cua_toi.html',
        context
    )
