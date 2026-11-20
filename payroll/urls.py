from django.urls import path
from . import views

app_name = 'payroll'
urlpatterns = [
    path('quan-ly/', views.salary_management, name='management'),
    path('phieu-luong/', views.my_payslip, name='my_payslip'),
    path('api/period/', views.payroll_data, name='data'),
    path('api/action/', views.payroll_action, name='action'),
    path('api/me/', views.employee_data, name='employee_data'),
    path('api/feedback/', views.employee_feedback, name='feedback'),
]
