
from django.urls import path
from .views import (
    AccountLoginView,
    dashboard,
    register_view,
    about_view,
    help_page,
    module_placeholder,
)
from django.contrib.auth.views import LogoutView

app_name = 'accounts'

urlpatterns = [
    path('module/<slug:slug>/', module_placeholder, name='module'),
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
    path(
        'about/',
        about_view,
        name='about'
    ),
    path(
        'help/',
        help_page,
        name='help'
    ),
]

