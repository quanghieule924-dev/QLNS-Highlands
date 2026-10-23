
from django.urls import path
from .views import AccountLoginView, dashboard

app_name = 'accounts'

urlpatterns = [
    path(
        'login/',
        AccountLoginView.as_view(),
        name='login'
    ),

    path(
        'dashboard/',
        dashboard,
        name='dashboard'
    ),
]
