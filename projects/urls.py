from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_dashboard/add_project/', views.add_project, name='add_project'),
    path('admin_dashboard/add_employee/', views.add_employee, name='add_employee'),
    path('admin_dashboard/project/<int:project_id>/', views.project_details, name='project_detail'),
    path('admin_dashboard/edit_project/<int:project_id>/', views.edit_project, name='edit_project'),
    path('admin_dashboard/delete_project/<int:project_id>/', views.delete_project, name='delete_project'),
    path('employee_dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('admin_dashboard/delete_employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('skill_measurement/', views.skill_measurement, name='skill_measurement'),
    path('assign_task/', views.assign_task, name='assign_task'),
    path('update_task_status/', views.update_task_status, name='update_task_status'),
    path('update_project_status/', views.update_project_status, name='update_project_status'),
    path('mark_project_completed/', views.mark_project_completed, name='mark_project_completed'),
]