from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import render

class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    next_page = reverse_lazy('accounts:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.POST.get('remember_me'):
            self.request.session.set_expiry(0)  # Đóng trình duyệt: hết phiên
        return response


# Trang đích tạm sau đăng nhập, trước khi nhóm xây dựng dashboard theo vai trò.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    return render(request, 'accounts/dashboard.html')

def register_view(request):
    return render(request, 'accounts/register.html')
