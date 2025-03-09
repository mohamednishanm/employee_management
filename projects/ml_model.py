import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer
from django.conf import settings
import os
import pickle
import json

from projects.models import EmployeeProfile, SkillMeasurement, Project

class TeamRecommender:
    def __init__(self):
        self.mlb = None
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models')
        self.ensure_model_dir()
        
    def ensure_model_dir(self):
        """Ensure the model directory exists"""
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
    
    def prepare_employee_data(self, include_unavailable=False):
        """Prepare employee data from the database"""
        # Get all employees
        employees = EmployeeProfile.objects.all()
        
        employee_data = []
        for employee in employees:
            # Check if employee is available (not assigned to any in-progress project)
            is_available = True
            if not include_unavailable:  # Skip availability check if we want all employees
                active_projects = employee.projects.filter(status__in=['pending', 'in_progress'])
                if active_projects.exists():
                    is_available = False
            
            # Only include available employees unless specified
            if is_available or include_unavailable:
                # Get skill measurements for this employee
                skill_measurements = SkillMeasurement.objects.filter(employee=employee)
                
                # Create skill and proficiency lists
                skills = []
                proficiency_levels = {}
                
                for skill in skill_measurements:
                    skills.append(skill.skill_name)
                    proficiency_levels[skill.skill_name] = skill.proficiency
                
                # Calculate leadership score based on skills and proficiency
                leadership_score = self.calculate_leadership_score(skill_measurements)
                
                employee_data.append({
                    'employee_id': employee.id,
                    'employee_name': employee.user.username,
                    'login_id': employee.login_id,
                    'role': employee.role,
                    'skills': skills,
                    'proficiency_levels': proficiency_levels,
                    'user_id': employee.user.id,
                    'is_available': is_available,
                    'leadership_score': leadership_score
                })
        
        return pd.DataFrame(employee_data)
    
    def calculate_leadership_score(self, skill_measurements):
        """Calculate a leadership score based on skill diversity and proficiency"""
        if not skill_measurements:
            return 0
        
        # More skills and higher proficiency levels indicate better leadership potential
        num_skills = len(skill_measurements)
        avg_proficiency = sum(skill.proficiency for skill in skill_measurements) / num_skills if num_skills > 0 else 0
        
        # Leadership score formula: skill count * average proficiency
        # This favors employees with both breadth and depth of skills
        leadership_score = num_skills * avg_proficiency
        
        return leadership_score
    
    def fit_transform_skills(self, employee_df):
        """Fit and transform skills using MultiLabelBinarizer"""
        self.mlb = MultiLabelBinarizer()
        skills_encoded = self.mlb.fit_transform(employee_df["skills"])
        
        # Save the mlb for later use
        with open(os.path.join(self.model_path, 'mlb.pkl'), 'wb') as f:
            pickle.dump(self.mlb, f)
        
        return skills_encoded
    
    def create_proficiency_matrix(self, employee_df):
        """Create a proficiency matrix for employees"""
        proficiency_matrix = []
        for _, row in employee_df.iterrows():
            proficiency = [row["proficiency_levels"].get(skill, 0) for skill in self.mlb.classes_]
            proficiency_matrix.append(proficiency)
        return np.array(proficiency_matrix)
    
    def recommend_team(self, required_skills, team_size):
        """Recommend a team based on required skills and team size"""
        # Load the MultiLabelBinarizer
        if self.mlb is None:
            try:
                with open(os.path.join(self.model_path, 'mlb.pkl'), 'rb') as f:
                    self.mlb = pickle.load(f)
            except FileNotFoundError:
                # If mlb.pkl doesn't exist, we need to generate it
                # Use all employees (including unavailable) for training
                employee_df = self.prepare_employee_data(include_unavailable=True)
                self.fit_transform_skills(employee_df)
        
        # Prepare employee data (only available employees)
        employee_df = self.prepare_employee_data(include_unavailable=False)
        
        # If no available employees, return empty recommendation
        if employee_df.empty:
            return pd.DataFrame(), None
        
        # Get skills of available employees
        skills_encoded = self.mlb.transform(employee_df["skills"])
        
        # Create proficiency matrix
        proficiency_matrix = self.create_proficiency_matrix(employee_df)
        
        # Weighted skill matrix
        weighted_skills_matrix = skills_encoded * proficiency_matrix
        
        # Process required skills
        try:
            project_skills_vector = np.array([1 if skill in required_skills else 0 for skill in self.mlb.classes_])
        except AttributeError:
            # If mlb.classes_ doesn't exist, we need to regenerate
            employee_df_all = self.prepare_employee_data(include_unavailable=True)
            self.fit_transform_skills(employee_df_all)
            project_skills_vector = np.array([1 if skill in required_skills else 0 for skill in self.mlb.classes_])
        
        # Calculate similarity scores
        similarity_scores = cosine_similarity([project_skills_vector], weighted_skills_matrix)[0]
        employee_df["similarity_score"] = similarity_scores
        
        # Sort employees by similarity score
        recommended_team = employee_df.sort_values(by="similarity_score", ascending=False)
        recommended_team = recommended_team.head(min(team_size, len(employee_df)))
        
        # Select team leader based on combined similarity score and leadership score
        combined_scores = recommended_team.copy()
        combined_scores['combined_score'] = combined_scores['similarity_score'] * 0.7 + combined_scores['leadership_score'] * 0.3
        team_leader = combined_scores.sort_values(by='combined_score', ascending=False).iloc[0]
        
        print(f"Selected team leader: {team_leader['employee_name']} with combined score {team_leader['combined_score']}")
        
        return recommended_team, team_leader

# Create a singleton instance of the recommender
recommender = TeamRecommender()