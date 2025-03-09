import random
import string
from django.http import JsonResponse
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from projects.models import EmployeeProfile, Project, SkillMeasurement, Task  # Added Task import
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt


def login_view(request):
    if request.method == 'POST':
        login_id = request.POST.get('login_id')
        password = request.POST.get('password')
        role = request.POST.get('role')

        print(f"Login attempt - ID: {login_id}, Password: {password}, Role: {role}")  # Debug print

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
                print(f"Found employee: {employee_profile.user.username}, Stored password: {employee_profile.password}")  # Debug print
                
                # Check if password matches (comparing with stored plain password)
                if employee_profile.password == password:
                    # Login the user
                    login(request, employee_profile.user)
                    print(f"Login successful for: {employee_profile.user.username}")  # Debug print
                    
                    # Check if employee has completed skill assessment
                    skill_count = SkillMeasurement.objects.filter(employee=employee_profile).count()
                    print(f"Skill count: {skill_count}")  # Debug print
                    
                    # If no skills submitted yet, redirect to skill measurement
                    if skill_count == 0:
                        return redirect('skill_measurement')
                    else:
                        return redirect('employee_dashboard')
                else:
                    print(f"Password mismatch. Input: {password}, Stored: {employee_profile.password}")  # Debug print
                    return render(request, 'login.html', {'error': 'Invalid password.'})
                    
            except EmployeeProfile.DoesNotExist:
                print(f"No employee found with login_id: {login_id}")  # Debug print
                return render(request, 'login.html', {'error': 'Invalid employee login ID.'})
            except Exception as e:
                # For debugging purposes, capture and display any other errors
                print(f"Login error: {str(e)}")  # Debug print
                return render(request, 'login.html', {'error': f'Login error: {str(e)}'})

    return render(request, 'login.html')

@login_required
def admin_dashboard(request):
    # Ensure only superusers can access this dashboard
    if not request.user.is_superuser:
        return redirect('login')  # Redirect to login if not an admin
    
    # Get all projects
    projects = Project.objects.all().order_by('-created_at')
    
    return render(request, 'admin_dashboard.html', {'projects': projects})

@login_required
def add_project(request):
    # Only admins should access this page
    if not request.user.is_superuser:
        return redirect('login')
    
    # Import ML model here to avoid circular imports
    from .ml_model import recommender
    
    if request.method == 'POST':
        # Process form submission
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        deadline = request.POST.get('deadline')
        num_employees = int(request.POST.get('num_employees', 1))
        
        # Get selected technologies
        try:
            selected_technologies = json.loads(request.POST.get('selected_technologies', '[]'))
        except json.JSONDecodeError:
            selected_technologies = []
        
        # Check if assign employees button was clicked
        if 'assign_team' in request.POST:
            # Use the ML model to recommend a team
            recommended_team, team_leader = recommender.recommend_team(selected_technologies, num_employees)
            
            # Check if we got enough team members
            if len(recommended_team) < num_employees:
                warning_message = f"Warning: Only {len(recommended_team)} available employees found. Some employees may be currently assigned to other projects."
            else:
                warning_message = None
            
            # Convert to list for template rendering
            team_members = []
            for _, employee in recommended_team.iterrows():
                # Check if this employee is the recommended leader
                is_leader = False
                if team_leader is not None and employee['employee_id'] == team_leader['employee_id']:
                    is_leader = True
                
                team_members.append({
                    'id': int(employee['employee_id']),
                    'name': employee['employee_name'],
                    'role': employee['role'],
                    'match': f"{employee['similarity_score'] * 100:.2f}%",
                    'leader': is_leader
                })
            
            # Render the same page with team recommendations
            return render(request, 'add_project.html', {
                'tech_stacks': json.dumps(get_tech_stacks()),
                'recommended_team': team_members,
                'warning_message': warning_message,
                'team_leader': team_leader['employee_id'] if team_leader is not None else None,
                'form_data': {
                    'title': title,
                    'description': description,
                    'start_date': start_date,
                    'deadline': deadline,
                    'num_employees': num_employees,
                    'selected_technologies': selected_technologies
                }
            })
        
        # Check if create project button was clicked
        elif 'create_project' in request.POST:
            # Get the selected team members
            selected_members = []
            for key in request.POST:
                if key.startswith('team_member_'):
                    employee_id = int(key.replace('team_member_', ''))
                    selected_members.append(employee_id)
            
            # Check if there's a team leader
            team_leader_id = None
            for key in request.POST:
                if key == 'team_leader':
                    team_leader_id = int(request.POST[key])
            
            # Create the project
            project = Project.objects.create(
                title=title,
                description=description,
                start_date=start_date,
                deadline=deadline,
                status='pending',
                technologies=selected_technologies
            )
            
            # Assign team members to the project
            for employee_id in selected_members:
                try:
                    employee = EmployeeProfile.objects.get(id=employee_id)
                    
                    # Check if employee is available
                    active_projects = employee.projects.filter(status__in=['pending', 'in_progress'])
                    if not active_projects.exists():
                        # Add employee to the project
                        employee.projects.add(project)
                        
                        # Set leader status
                        if employee_id == team_leader_id:
                            # First, reset leader status for this employee on all projects
                            employee.is_leader = True
                            employee.save()
                except Exception as e:
                    print(f"Error assigning employee {employee_id}: {str(e)}")
            
            return redirect('admin_dashboard')
    
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
        
        # Get projects assigned to this employee
        assigned_projects = employee.projects.all()
        
        # Get active projects (pending or in-progress)
        active_projects = assigned_projects.filter(status__in=['pending', 'in_progress'])
        
        # We'll use a dictionary to store team members for each project
        projects_team_members = {}
        
        # For each project, get the team members
        for project in active_projects:
            # Get all team members for this project
            team_members_for_project = EmployeeProfile.objects.filter(projects=project)
            
            # Store in dictionary
            projects_team_members[project.id] = team_members_for_project
        
        # Get tasks assigned to this employee
        try:
            assigned_tasks = Task.objects.filter(assigned_to=request.user)
        except:
            assigned_tasks = []
        
        # Check if employee is a team leader for any active project
        is_team_leader = employee.is_leader
        led_projects = []
        team_members = []
        
        if is_team_leader:
            # Find projects where this employee is a leader
            for project in active_projects:
                # Get all project members except the current employee
                project_members = EmployeeProfile.objects.filter(projects=project).exclude(id=employee.id)
                
                # If this project has members, add to led_projects
                if project_members.exists():
                    led_projects.append(project)
                    # Add team members
                    for member in project_members:
                        team_members.append({
                            'id': member.id,
                            'name': member.user.username,
                            'role': member.role,
                            'email': member.user.email,
                            'project_id': project.id,
                            'project_title': project.title
                        })
        
        context = {
            'employee': employee,
            'assigned_projects': assigned_projects,
            'active_projects': active_projects,
            'assigned_tasks': assigned_tasks,
            'is_team_leader': is_team_leader,
            'led_projects': led_projects,
            'team_members': team_members,
            'projects_team_members': projects_team_members
        }
        
        return render(request, 'employee_dashboard.html', context)
    except Exception as e:
        print(f"Employee dashboard error: {str(e)}")
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
    
    # Create a dictionary to store existing ratings - make sure keys are strings
    existing_ratings = {}
    for skill in existing_skills:
        for key, tech in tech_stacks.items():
            if tech == skill.skill_name:
                # Convert key to string and the proficiency to string for comparison in template
                existing_ratings[str(key)] = str(skill.proficiency)
                break
    
    print(f"Existing ratings: {existing_ratings}")  # Debugging output
    
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
                    skill_name=tech,
                    proficiency=int(skill_value)
                )
        
        # Redirect to employee dashboard after submission
        return redirect('employee_dashboard')
    
    # Prepare ratings in a more template-friendly format
    formatted_ratings = []
    for key, tech in tech_stacks.items():
        # Try to find existing rating
        rating = None
        for skill in existing_skills:
            if skill.skill_name == tech:
                rating = str(skill.proficiency)
                break
        
        formatted_ratings.append({
            'key': key,
            'tech': tech,
            'rating': rating
        })
    
    context = {
        "tech_stacks": tech_stacks,
        "existing_ratings": existing_ratings,
        "formatted_ratings": formatted_ratings  # New format that doesn't require custom filter
    }
    
    return render(request, "skill_measurement.html", context)

@login_required
def project_details(request, project_id):
    # Ensure only superusers can access this view
    if not request.user.is_superuser:
        return redirect('login')
    
    # Get the project
    project = get_object_or_404(Project, id=project_id)
    
    # Get team members assigned to this project
    team_members = EmployeeProfile.objects.filter(projects=project)
    
    # Find the team leader for this project
    team_leader = team_members.filter(is_leader=True).first()
    
    # Get tasks associated with this project (if Task model exists)
    try:
        tasks = Task.objects.filter(project=project)
    except:
        tasks = []
    
    context = {
        'project': project,
        'team_members': team_members,
        'tasks': tasks,
        'team_leader': team_leader
    }
    
    return render(request, 'project_details.html', context)

@login_required
def edit_project(request, project_id):
    # Ensure only superusers can access this view
    if not request.user.is_superuser:
        return redirect('login')
    
    # Get the project
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        # Process form submission
        project.description = request.POST.get('description')
        project.deadline = request.POST.get('deadline')
        project.status = request.POST.get('status')
        
        # Save project
        project.save()
        
        # Check if there are tasks to create/update
        task_names = request.POST.getlist('task_name')
        task_deadlines = request.POST.getlist('task_deadline')
        task_assignees = request.POST.getlist('task_assignee')
        
        # If Task model exists, update tasks
        try:
            # Clear existing tasks if needed
            if request.POST.get('clear_tasks'):
                Task.objects.filter(project=project).delete()
            
            # Create new tasks
            for i in range(len(task_names)):
                if task_names[i] and task_deadlines[i] and task_assignees[i]:
                    assigned_user = User.objects.get(id=task_assignees[i])
                    Task.objects.create(
                        project=project,
                        task_name=task_names[i],
                        deadline=task_deadlines[i],
                        status='pending',
                        assigned_to=assigned_user
                    )
        except:
            pass
        
        return redirect('project_detail', project_id=project.id)
    
    # Get team members assigned to this project
    team_members = EmployeeProfile.objects.filter(projects=project)
    
    # Get all employees for task assignment
    all_employees = EmployeeProfile.objects.all()
    
    # Get tasks associated with this project (if Task model exists)
    try:
        tasks = Task.objects.filter(project=project)
    except:
        tasks = []
    
    context = {
        'project': project,
        'team_members': team_members,
        'all_employees': all_employees,
        'tasks': tasks
    }
    
    return render(request, 'edit_project.html', context)

@login_required
def delete_project(request, project_id):
    # Ensure only superusers can access this view
    if not request.user.is_superuser:
        return redirect('login')
    
    if request.method == 'POST':
        # Get the project
        project = get_object_or_404(Project, id=project_id)
        
        # Remove team member associations
        for employee in EmployeeProfile.objects.filter(projects=project):
            employee.projects.remove(project)
            
            # If employee is a leader for this project, update leader status
            if employee.is_leader:
                # Check if this employee is a leader for any other projects
                other_led_projects = employee.projects.all().exclude(id=project_id)
                if not other_led_projects.exists():
                    employee.is_leader = False
                    employee.save()
        
        # Delete tasks associated with the project (if Task model exists)
        try:
            Task.objects.filter(project=project).delete()
        except:
            pass
        
        # Delete the project
        project.delete()
    
    return redirect('admin_dashboard')

@login_required
def assign_task(request):
    # Check if user is an employee (not an admin)
    if request.user.is_superuser:
        return redirect('login')
    
    # Check if the user is a team leader
    try:
        employee = request.user.employeeprofile
        if not employee.is_leader:
            return redirect('employee_dashboard')
    except:
        return redirect('login')
    
    if request.method == 'POST':
        # Get form data
        team_member_id = request.POST.get('team_member')
        project_id = request.POST.get('project')
        task_name = request.POST.get('task_name')
        deadline = request.POST.get('deadline')
        
        if not team_member_id or not project_id or not task_name or not deadline:
            # Missing required fields
            return redirect('employee_dashboard')
        
        try:
            # Get the team member's profile and user
            team_member = EmployeeProfile.objects.get(id=team_member_id)
            assigned_user = team_member.user
            
            # Get the project
            project = Project.objects.get(id=project_id)
            
            # Verify this leader is assigned to this project and is a leader
            leader_projects = employee.projects.filter(id=project_id)
            if not leader_projects.exists():
                return redirect('employee_dashboard')
            
            # Create the task
            Task.objects.create(
                project=project,
                task_name=task_name,
                deadline=deadline,
                status='pending',
                assigned_to=assigned_user
            )
        except Exception as e:
            print(f"Error assigning task: {str(e)}")
        
        return redirect('employee_dashboard')
    
    # If not POST, redirect back to dashboard
    return redirect('employee_dashboard')

@login_required
def update_task_status(request):
    # Check if user is an employee (not an admin)
    if request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            task_id = data.get('task_id')
            status = data.get('status')
            
            # Validate the data
            if not task_id or not status:
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
            
            if status not in ['pending', 'in_progress', 'completed']:
                return JsonResponse({'status': 'error', 'message': 'Invalid status value'}, status=400)
            
            # Get the task
            task = Task.objects.get(id=task_id)
            
            # Check if the task is assigned to this user
            if task.assigned_to != request.user:
                return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
            
            # Update the task status
            task.status = status
            task.save()
            
            return JsonResponse({'status': 'success', 'message': 'Task status updated'})
            
        except Task.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@login_required
def update_project_status(request):
    """
    View for team leaders to update project status
    """
    # Check if user is an employee (not an admin)
    if request.user.is_superuser:
        return redirect('login')
    
    # Check if the user is a team leader
    try:
        employee = request.user.employeeprofile
        if not employee.is_leader:
            return redirect('employee_dashboard')
    except:
        return redirect('login')
    
    if request.method == 'POST':
        # Get form data
        project_id = request.POST.get('project_id')
        new_status = request.POST.get('status')
        
        # Validate the data
        if not project_id or not new_status:
            return redirect('employee_dashboard')
        
        # Get the project
        try:
            project = Project.objects.get(id=project_id)
            
            # Verify this employee is assigned to this project
            user_projects = employee.projects.filter(id=project_id)
            if not user_projects.exists():
                return redirect('employee_dashboard')
            
            # Update the project status
            project.status = new_status
            project.save()
            
            # Redirect back to dashboard
            return redirect('employee_dashboard')
        except Project.DoesNotExist:
            return redirect('employee_dashboard')
    
    # If not POST, redirect back to dashboard
    return redirect('employee_dashboard')

@login_required
def mark_project_completed(request):
    """
    View for admin to mark a project as completed
    """
    # Ensure only superusers can access this view
    if not request.user.is_superuser:
        return redirect('login')
    
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                
                # Mark the project as completed
                project.status = 'completed'
                project.save()
                
            except Project.DoesNotExist:
                pass
    
    return redirect('admin_dashboard')