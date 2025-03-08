import random
import string
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from projects.models import EmployeeProfile, Project, SkillMeasurement
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password


def login_view(request):
    if request.method == 'POST':
        login_id = request.POST.get('login_id')
        password = request.POST.get('password')
        role = request.POST.get('role')

        # Admin Login
        if role == 'admin':
            user = authenticate(request, username=login_id, password=password)
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                return render(request, 'login.html', {'error': 'Invalid admin credentials or role.'})

        # Employee Login
        elif role == 'employee':
            try:
                # Check if the login_id matches an employee
                employee_profile = EmployeeProfile.objects.get(login_id=login_id)
                
                # Check if password matches (comparing with stored plain password)
                if employee_profile.password == password:
                    # Login the user
                    login(request, employee_profile.user)
                    
                    # Check if employee has completed skill assessment
                    skill_count = SkillMeasurement.objects.filter(employee=employee_profile).count()
                    
                    # If no skills submitted yet, redirect to skill measurement
                    if skill_count == 0:
                        return redirect('skill_measurement')
                    else:
                        return redirect('employee_dashboard')
                else:
                    return render(request, 'login.html', {'error': 'Invalid password.'})
                    
            except EmployeeProfile.DoesNotExist:
                return render(request, 'login.html', {'error': 'Invalid employee login ID.'})

    return render(request, 'login.html')

@login_required
def admin_dashboard(request):
    # Ensure only superusers can access this dashboard
    if not request.user.is_superuser:
        return redirect('login')  # Redirect to login if not an admin
    return render(request, 'admin_dashboard.html')


@login_required
def add_project(request):
    # Only admins should access this page
    if not request.user.is_superuser:
        return redirect('login')
    
    if request.method == 'POST':
        # Process form submission
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        deadline = request.POST.get('deadline')
        num_employees = request.POST.get('num_employees')
        
        # Get selected technologies
        try:
            selected_technologies = json.loads(request.POST.get('selected_technologies', '[]'))
        except json.JSONDecodeError:
            selected_technologies = []
        
        # Create project (implementation depends on your model structure)
        # Project.objects.create(...)
        
        return redirect('admin_dashboard')  # Redirect after successful creation
    
    # Get tech stacks from the same source as skill measurement
    tech_stacks = get_tech_stacks()
    
    return render(request, 'add_project.html', {'tech_stacks': json.dumps(tech_stacks)})

@login_required
def add_employee(request):
    # Only admins should access this page
    if not request.user.is_superuser:
        return redirect('login')
    
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        phone_number = request.POST['phone_number']
        role = request.POST['role']

        # Generate a random password
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        # Hash the password
        hashed_password = make_password(password)

        # Generate a unique login_id
        login_id = name[:3].lower() + ''.join(random.choices(string.digits, k=4))

        # Create a new user with the hashed password
        user = User.objects.create_user(
            username=email,  
            email=email,
            password=hashed_password
        )

        # Create an EmployeeProfile and store the plain text password
        employee_profile = EmployeeProfile.objects.create(
            user=user,
            login_id=login_id,
            phone_number=phone_number,
            role=role,
            password=password  # Store the plain text password for display
        )

        return redirect('add_employee')

    # Fetch the employee list to display
    employees = EmployeeProfile.objects.all()

    # Render the template with employee data
    return render(request, 'add_employee.html', {'employees': employees})

@login_required
def delete_employee(request, employee_id):
    # Only admins should be able to delete employees
    if not request.user.is_superuser:
        return redirect('login')

    # Get the employee profile to delete
    employee = get_object_or_404(EmployeeProfile, id=employee_id)

    # Delete the employee profile and the associated user
    user = employee.user
    employee.delete()  # Delete the EmployeeProfile
    user.delete()  # Delete the associated User model instance

    return redirect('add_employee')
# def emp(request):
#     return render(request, 'employee_dashboard.html')

@login_required
def employee_dashboard(request):
    # Ensure only non-superusers can access this dashboard
    if request.user.is_superuser:
        return redirect('login')  # Redirect to login if it's an admin
    
    # Get the current employee's profile
    try:
        employee = request.user.employeeprofile
        context = {
            'employee': employee
        }
        return render(request, 'employee_dashboard.html', context)
    except:
        return redirect('login')  # Redirect if no employee profile exists


def logout_view(request):
    logout(request)
    return redirect('login') 

# Function to get tech stacks
def get_tech_stacks():
    tech_stacks = {
        0: "JavaScript",
        1: "React.js",
        2: "Angular",
        3: "Vue.js",
        4: "Node.js",
        5: "Express.js",
        6: "MongoDB",
        7: "Python",
        8: "Django",
        9: "Flask",
        10: "SQL",
        11: "PostgreSQL",
        12: "MySQL",
        13: "Docker",
        14: "Kubernetes",
        15: "AWS",
        16: "Azure",
        17: "Google Cloud",
        18: "PHP",
        19: "Laravel",
        20: "Ruby on Rails",
        21: "Java",
        22: "Spring Boot",
        23: "GraphQL",
        24: "Redux",
        25: "TypeScript",
        26: "C#",
        27: ".NET",
        28: "Go",
        29: "Swift",
    }
    return tech_stacks

@login_required
def skill_measurement(request):
    # Ensure only non-superusers can access this page
    if request.user.is_superuser:
        return redirect('login')
    
    # Get the standardized tech stacks
    tech_stacks = get_tech_stacks()
    
    # Get the employee profile
    try:
        employee_profile = request.user.employeeprofile
    except:
        return redirect('login')
    
    # Get existing skill measurements for this employee
    existing_skills = SkillMeasurement.objects.filter(employee=employee_profile)
    
    # Create a dictionary to store existing ratings
    existing_ratings = {}
    for skill in existing_skills:
        for key, tech in tech_stacks.items():
            if tech == skill.skill_name:  # Changed from skill.technology
                existing_ratings[str(key)] = skill.proficiency  # Changed from skill.proficiency_level
                break
    
    if request.method == 'POST':
        # Process the submitted skill ratings
        
        # Clear existing skills for this employee
        SkillMeasurement.objects.filter(employee=employee_profile).delete()
        
        # Save new skills
        for key, tech in tech_stacks.items():
            skill_value = request.POST.get(f'tech_{key}')
            if skill_value:
                SkillMeasurement.objects.create(
                    employee=employee_profile,
                    skill_name=tech,  # Changed from technology
                    proficiency=int(skill_value)  # Changed from proficiency_level
                )
        
        # Redirect to employee dashboard after submission
        return redirect('employee_dashboard')
    
    return render(request, "skill_measurement.html", {
        "tech_stacks": tech_stacks,
        "existing_ratings": existing_ratings
    })