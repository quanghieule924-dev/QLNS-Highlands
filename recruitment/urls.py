# recruitment/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Đoạn này khai báo phần đuôi: /tong-quan/
    path('tong-quan/', views.recruitment_overview, name='overview'),
]