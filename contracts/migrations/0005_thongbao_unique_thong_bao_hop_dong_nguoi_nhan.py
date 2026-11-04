from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0004_alter_hopdong_trang_thai_hd'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Cập nhật trạng thái migration, không thêm cột vào database
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='thongbao',
                    name='nguoi_nhan',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        db_column='Nguoi_nhan',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='thong_bao',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Người nhận'
                    ),
                ),
            ],
        ),

        # Tạo ràng buộc duy nhất
        migrations.AddConstraint(
            model_name='thongbao',
            constraint=models.UniqueConstraint(
                fields=('hop_dong', 'nguoi_nhan'),
                name='unique_thong_bao_hop_dong_nguoi_nhan'
            ),
        ),
    ]