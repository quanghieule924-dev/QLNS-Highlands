
from django.urls import path
from . import views

app_name = 'scheduling'

urlpatterns = [
    path(
        'dashboard/',
        views.scheduling_dashboard,
        name='dashboard'
    ),
]
