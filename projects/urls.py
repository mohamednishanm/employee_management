from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_dashboard/add_project/', views.add_project, name='add_project'),
    path('admin_dashboard/add_employee/', views.add_employee, name='add_employee'),
    path('employee_dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('admin_dashboard/delete_employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('skill_measurement/', views.skill_measurement, name='skill_measurement'),
    # path('emp/', views.emp, name='emp'),
]
