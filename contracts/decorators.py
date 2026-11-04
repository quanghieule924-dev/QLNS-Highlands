
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    Chỉ cho phép người dùng có vai trò được chỉ định truy cập.

    Người dùng chưa đăng nhập sẽ được chuyển đến trang đăng nhập.
    Người dùng không đúng vai trò sẽ nhận lỗi 403.
    """

    def decorator(view_func):

        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if request.user.role not in roles:
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
