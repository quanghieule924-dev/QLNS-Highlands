
from django import forms
from django.forms import inlineformset_factory
from employees.models import NhanVien

from .models import (
    HopDong,
    ThongBao,
    BHXH,
    CheDoPhucLoi,
    PhucLoiHopDong,
    PhuCap,

)

from django.utils import timezone

# =========================================================
# 1. FORM QUẢN LÝ HỢP ĐỒNG
# =========================================================

class HopDongForm(forms.ModelForm):

    class Meta:
        model = HopDong
        fields = [
            'so_hd',
            'nhan_vien',
            'hop_dong_truoc',
            'loai_hd',
            'ngay_bat_dau',
            'ngay_ket_thuc',
            'hinh_thuc_luong',
            'muc_luong',
        ]
        widgets = {
            'mahd': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã hợp đồng',
            }),
            'so_hd': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập số hợp đồng',
            }),
            'nhan_vien': forms.Select(attrs={
                'class': 'form-control',
            }),
            'hop_dong_truoc': forms.Select(attrs={
                'class': 'form-control',
            }),
            'loai_hd': forms.Select(attrs={
                'class': 'form-control',
            }),
            'ngay_bat_dau': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'ngay_ket_thuc': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'ngay_ky': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'hinh_thuc_luong': forms.Select(attrs={
                'class': 'form-control',
            }),
            'muc_luong': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mức lương',
                'min': '0.01',
                'step': '0.01',
            }),
            'trang_thai_hd': forms.Select(attrs={
                'class': 'form-control',
            }),
        }


#Mới thêm ngày 6/11
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            # Chỉ cho phép chọn nhân viên đã hoàn thành đào tạo
            self.fields['nhan_vien'].queryset = (
                NhanVien.objects.filter(
                    trang_thai='Chính thức'
                ).order_by('ho_ten')
            )


class GiaHanHopDongForm(forms.ModelForm):

    class Meta:
        model = HopDong
        fields = [
            'so_hd',
            'ngay_ket_thuc',
            'hinh_thuc_luong',
            'muc_luong',
        ]

        widgets = {
            'so_hd': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập số hợp đồng mới',
            }),
            'ngay_ket_thuc': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'hinh_thuc_luong': forms.Select(attrs={
                'class': 'form-control',
            }),
            'muc_luong': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mức lương',
                'min': '0.01',
                'step': '0.01',
            }),
        }


# =========================================================
# 2. FORM THÔNG BÁO HỢP ĐỒNG
# =========================================================

class ThongBaoForm(forms.ModelForm):

    class Meta:
        model = ThongBao
        fields = [
            'matb',
            'hop_dong',
            'noi_dung',
            'trang_thai',
        ]

        widgets = {
            'matb': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã thông báo',
            }),
            'hop_dong': forms.Select(attrs={
                'class': 'form-control',
            }),
            'noi_dung': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Nhập nội dung thông báo',
            }),
            'trang_thai': forms.Select(attrs={
                'class': 'form-control',
            }),
        }


# =========================================================
# 5. FORM QUẢN LÝ BẢO HIỂM XÃ HỘI
# =========================================================

class BHXHForm(forms.ModelForm):

    class Meta:
        model = BHXH
        fields = [
            'mabh',
            'hop_dong',
            'ma_so_bh',
            'muc_dong',
            'ngay_tham_gia',
            'trang_thai',
        ]

        widgets = {
            'mabh': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã BHXH',
            }),
            'hop_dong': forms.Select(attrs={
                'class': 'form-control',
            }),
            'ma_so_bh': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã số BHXH',
            }),
            'muc_dong': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
            }),
            'ngay_tham_gia': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'trang_thai': forms.Select(attrs={
                'class': 'form-control',
            }),
        }


# =========================================================
# 6. FORM DANH MỤC CHẾ ĐỘ PHÚC LỢI
# =========================================================

class CheDoPhucLoiForm(forms.ModelForm):

    class Meta:
        model = CheDoPhucLoi
        fields = [
            'ten_pl',
            'mo_ta',
            'dieu_kien_huong',
        ]

        widgets = {
            'mapl': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã phúc lợi',
            }),
            'ten_pl': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tên chế độ phúc lợi',
            }),
            'mo_ta': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Mô tả chế độ phúc lợi',
            }),
            'dieu_kien_huong': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nhập điều kiện được hưởng',
            }),
        }


# =========================================================
# 7. FORM PHÚC LỢI ÁP DỤNG CHO HỢP ĐỒNG
# =========================================================

class PhucLoiHopDongForm(forms.ModelForm):

    class Meta:
        model = PhucLoiHopDong
        fields = [
            'maplhd',
            'hop_dong',
            'che_do',
            'gia_tri',
        ]

        widgets = {
            'maplhd': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã phúc lợi hợp đồng',
            }),
            'hop_dong': forms.Select(attrs={
                'class': 'form-control',
            }),
            'che_do': forms.Select(attrs={
                'class': 'form-control',
            }),
            'gia_tri': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
            }),
        }


# =========================================================
# 8. FORM QUẢN LÝ PHỤ CẤP
# =========================================================

class PhuCapForm(forms.ModelForm):

    class Meta:
        model = PhuCap
        fields = [
            'mapc',
            'hop_dong',
            'loai_pc',
            'gia_tri',
            'thang_ap_dung',
        ]

        widgets = {
            'mapc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập mã phụ cấp',
            }),
            'hop_dong': forms.Select(attrs={
                'class': 'form-control',
            }),
            'loai_pc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: Phụ cấp ăn uống',
            }),
            'gia_tri': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
            }),
            'thang_ap_dung': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'YYYY-MM, ví dụ 2026-11',
            }),
        }



# =========================================================
# 9. FORM chấm dứt hợp đồng
# =========================================================
class ChamDutHopDongForm(forms.ModelForm):

    class Meta:
        model = HopDong
        fields = [
            'ngay_cham_dut',
            'ly_do_cham_dut',
        ]

        widgets = {
            'ngay_cham_dut': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),

            'ly_do_cham_dut': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Nhập lý do chấm dứt hợp đồng',
            }),
        }

    def clean_ngay_cham_dut(self):
        ngay_cham_dut = self.cleaned_data.get('ngay_cham_dut')

        if ngay_cham_dut and ngay_cham_dut > timezone.localdate():
            raise forms.ValidationError(
                'Ngày chấm dứt không được lớn hơn ngày hiện tại.'
            )

        return ngay_cham_dut



