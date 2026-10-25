
from django.urls import path
from .views import AccountLoginView, dashboard, register_view
from django.contrib.auth.views import LogoutView

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

    path(
        'register/',
        register_view,
        name='register'
    ),

    path(
        'logout/',
        LogoutView.as_view(),
        name='logout'
    ),
]

