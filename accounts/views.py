
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy


class AccountLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user

        if user.role == 'candidate':
            return reverse_lazy('home')

        return reverse_lazy('accounts:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)

        if not self.request.POST.get('remember_me'):
            self.request.session.set_expiry(0)

        return response


@login_required
def dashboard(request):
    # Ứng viên không được vào dashboard nội bộ
    if request.user.role == 'candidate':
        return redirect('home')

    # Chỉ quản lý và nhân viên được vào dashboard
    if request.user.role not in ['admin', 'employee']:
        return redirect('home')

    return render(
        request,
        'accounts/dashboard.html',
        {
            'role': request.user.role,
            'active_menu': 'dashboard',
        },
    )


def register_view(request):
    return render(request, 'accounts/register.html')
