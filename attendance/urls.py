
from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [

    path(
        'dashboard/',
        views.attendance_dashboard,
        name='dashboard'
    ),

    path(
        'employee/',
        views.employee_attendance_dashboard,
        name='employee_dashboard'
    ),

    path(
        'manager/',
        views.manager_attendance_dashboard,
        name='manager_dashboard'
    ),

    path(
        'kiosk/',
        views.attendance_kiosk,
        name='kiosk'
    ),

path(
    'enroll-face/',
    views.face_enrollment,
    name='face_enrollment'
),

path(
    'enroll-face/save/',
    views.save_face_enrollment,
    name='save_face_enrollment'
),

path(
    'kiosk/verify-face/',
    views.verify_kiosk_face,
    name='verify_kiosk_face'
),


path(
    'kiosk/today-shifts/',
    views.kiosk_today_shifts,
    name='kiosk_today_shifts'
),

path(
    'kiosk/record/',
    views.kiosk_record_attendance,
    name='kiosk_record_attendance'
),

path(
    'manager/history/',
    views.manager_attendance_history,
    name='manager_history'
),

path(
    'manager/export/',
    views.manager_attendance_export,
    name='manager_export'
),

path(
    'manager/face-station/',
    views.manager_face_station,
    name='manager_face_station'
),

]
