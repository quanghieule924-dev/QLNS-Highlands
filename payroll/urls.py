from django.urls import path
from . import views

app_name = 'payroll'
urlpatterns = [
    path('quan-ly/', views.salary_management, name='management'),
    path('phieu-luong/', views.my_payslip, name='my_payslip'),
]
