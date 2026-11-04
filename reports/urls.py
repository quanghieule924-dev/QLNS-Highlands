from django.urls import path
from .views import monthly_dashboard

app_name = 'reports'

urlpatterns = [
    path('monthly-dashboard/', monthly_dashboard, name='monthly_dashboard'),
]