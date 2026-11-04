from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction

from .models import User
from employees.models import NhanVien


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        return (
            *fieldsets,
            (
                'Phân quyền và liên kết nhân viên',
                {
                    'fields': (
                        'role',
                        'nhan_vien_lien_ket',
                    )
                }
            ),
        )

    def get_form(self, request, obj=None, **kwargs):
        base_form = (
            self.add_form if obj is None
            else self.form
        )

        class LinkedUserForm(base_form):
            nhan_vien_lien_ket = forms.ModelChoiceField(
                queryset=NhanVien.objects.none(),
                required=False,
                label='Hồ sơ nhân viên liên kết',
                help_text=(
                    'Chỉ hiển thị hồ sơ chưa liên kết '
                    'với tài khoản khác.'
                )
            )

            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)

                ds_nhan_vien = NhanVien.objects.filter(
                    tai_khoan__isnull=True
                )

                if obj is not None:
                    ds_nhan_vien = (
                        NhanVien.objects.filter(
                            tai_khoan__isnull=True
                        ) |
                        NhanVien.objects.filter(
                            tai_khoan=obj
                        )
                    )

                    nv_hien_tai = NhanVien.objects.filter(
                        tai_khoan=obj
                    ).first()

                    if nv_hien_tai:
                        self.fields[
                            'nhan_vien_lien_ket'
                        ].initial = nv_hien_tai.pk

                self.fields[
                    'nhan_vien_lien_ket'
                ].queryset = ds_nhan_vien.distinct()

                self.fields[
                    'nhan_vien_lien_ket'
                ].label_from_instance = (
                    lambda nv: f'{nv.manv} - {nv.ho_ten}'
                )

            def clean(self):
                cleaned_data = super().clean()

                nhan_vien = cleaned_data.get(
                    'nhan_vien_lien_ket'
                )

                role = cleaned_data.get(
                    'role',
                    getattr(self.instance, 'role', None)
                )

                if nhan_vien and role != 'employee':
                    self.add_error(
                        'nhan_vien_lien_ket',
                        'Chỉ tài khoản employee mới '
                        'được liên kết hồ sơ nhân viên.'
                    )

                return cleaned_data

        return super().get_form(
            request,
            obj,
            form=LinkedUserForm,
            **kwargs
        )

    @transaction.atomic
    def save_related(self, request, form, formsets, change):
        super().save_related(
            request, form, formsets, change
        )

        user = form.instance
        nhan_vien = form.cleaned_data.get(
            'nhan_vien_lien_ket'
        )

        # Bỏ liên kết cũ nếu quản trị viên đổi lựa chọn
        NhanVien.objects.filter(
            tai_khoan=user
        ).exclude(
            pk=nhan_vien.pk if nhan_vien else None
        ).update(tai_khoan=None)

        if nhan_vien:
            nhan_vien.tai_khoan = user
            nhan_vien.save(
                update_fields=['tai_khoan']
            )
