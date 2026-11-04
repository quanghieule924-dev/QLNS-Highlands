from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class InternalDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(username='manager_test', password='TestPass2026!', role='admin')
        self.employee = User.objects.create_user(username='employee_test', password='TestPass2026!', role='employee')
        self.candidate = User.objects.create_user(username='candidate_test', password='TestPass2026!', role='candidate')

    def test_manager_sees_dashboard(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tổng quan quản lý')
        self.assertContains(response, 'Nhân viên')

    def test_employee_sees_own_dashboard_not_management_stats(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Không gian nhân viên')
        self.assertNotContains(response, 'Tổng hồ sơ nhân viên hiện có')

    def test_candidate_cannot_access_internal_dashboard(self):
        self.client.force_login(self.candidate)
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertRedirects(response, reverse('home'))

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_employee_cannot_enter_recruitment_module(self):
        self.client.force_login(self.employee)
        response = self.client.get(reverse('accounts:module', args=['recruitment']))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_open_module_placeholder(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse('accounts:module', args=['recruitment']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chức năng đang được hoàn thiện')
