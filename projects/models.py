from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Project(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ])
    technologies = models.JSONField(default=list)  # Store tech stack as a list
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    task_name = models.CharField(max_length=200)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ])
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.task_name


class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    login_id = models.CharField(max_length=10, unique=True)
    phone_number = models.CharField(max_length=15)
    role = models.CharField(max_length=50)
    skills = models.JSONField(default=dict)
    projects = models.ManyToManyField('Project', related_name='team_members')
    is_leader = models.BooleanField(default=False, editable=False)
    password = models.CharField(max_length=128, blank=True)  # Store password

    def __str__(self):
        return f"{self.user.username} {'(Leader)' if self.is_leader else ''}"
    
class SkillMeasurement(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    skill_name = models.CharField(max_length=100)
    proficiency = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    measured_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.skill_name} - {self.proficiency} (Employee: {self.employee.user.username})"

