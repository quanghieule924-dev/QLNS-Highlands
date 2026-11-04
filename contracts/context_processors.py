from .models import ThongBao

def thong_bao_context(request):
    if not request.user.is_authenticated:
        return {}

    if request.user.role != 'admin':
        return {}

    thong_bao_moi_nhat = ThongBao.objects.filter(
        nguoi_nhan=request.user
    ).select_related(
        'hop_dong',
        'hop_dong__nhan_vien'
    ).order_by('-matb')

    so_thong_bao_chua_doc = thong_bao_moi_nhat.filter(
        trang_thai='chua_doc'
    ).count()

    return {
        'thong_bao_moi_nhat': thong_bao_moi_nhat[:10],
        'so_thong_bao_chua_doc': so_thong_bao_chua_doc,
    }