
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render


def home(request):
    return render(request, 'home.html')


urlpatterns = [
    path('admin/', admin.site.urls),

    # Trang chủ của nhóm
    path('', home, name='home'),

    # Các đường dẫn của app accounts
    path('accounts/', include('accounts.urls')),
]
