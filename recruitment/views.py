from django.shortcuts import render
from .models import Campaign, JobPosition, Applicant, Interview
from datetime import timedelta
from django.utils import timezone


def recruitment_overview(request):
    # Lấy các con số thống kê cho các Card
    open_campaigns_count = Campaign.objects.filter(is_open=True).count()
    hiring_positions_count = JobPosition.objects.filter(is_hiring=True).count()
    pending_applicants_count = Applicant.objects.filter(status='pending').count()

    # Tính số lượng lịch phỏng vấn trong 7 ngày tới
    now = timezone.now()
    next_7_days = now + timedelta(days=7)
    upcoming_interviews_count = Interview.objects.filter(
        scheduled_time__gte=now,
        scheduled_time__lte=next_7_days
    ).count()

    context = {
        'open_campaigns_count': open_campaigns_count,
        'hiring_positions_count': hiring_positions_count,
        'pending_applicants_count': pending_applicants_count,
        'upcoming_interviews_count': upcoming_interviews_count,
    }

    return render(request, 'recruitment/overview.html', context)