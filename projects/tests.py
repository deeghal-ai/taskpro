#projects/tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from datetime import date, datetime, timedelta
from decimal import Decimal
import uuid
import json

# Import models
from .models import (
    ProductSubcategory, Product, ProjectStatusOption, Project, 
    ProjectStatusHistory, ProductTask, ProjectTask, TaskAssignment,
    ActiveTimer, TimeSession, DailyTimeTotal, TimerActionLog,
    DailyRoster, Holiday, ProjectDelivery
)
from accounts.models import User
from locations.models import Region, City

# Import services and forms
from .services import ProjectService, ReportingService
from .forms import (
    ProjectCreateForm, ProjectStatusUpdateForm, ProjectFilterForm,
    ProjectTaskForm, TaskAssignmentForm, TaskAssignmentUpdateForm,
    TimerStopForm, ManualTimeEntryForm, EditSessionDurationForm,
    DailyRosterFilterForm, AddMiscHoursForm
)

User = get_user_model()

class ProductSubcategoryModelTests(TestCase):
    """Test cases for ProductSubcategory model"""
    
    def setUp(self):
        self.subcategory_data = {
            'name': 'Test Subcategory',
            'is_active': True
        }
    
    def test_create_subcategory(self):
        """Test creating a product subcategory"""
        subcategory = ProductSubcategory.objects.create(**self.subcategory_data)
        
        self.assertEqual(subcategory.name, 'Test Subcategory')
        self.assertTrue(subcategory.is_active)
        self.assertIsInstance(subcategory.id, uuid.UUID)
        self.assertIsNotNone(subcategory.created_at)
        self.assertIsNotNone(subcategory.updated_at)
    
    def test_subcategory_str_representation(self):
        """Test string representation"""
        subcategory = ProductSubcategory.objects.create(**self.subcategory_data)
        self.assertEqual(str(subcategory), 'Test Subcategory')
    
    def test_subcategory_name_uniqueness(self):
        """Test that subcategory names must be unique"""
        ProductSubcategory.objects.create(**self.subcategory_data)
        
        with self.assertRaises(IntegrityError):
            ProductSubcategory.objects.create(**self.subcategory_data)
    
    def test_subcategory_ordering(self):
        """Test subcategory ordering by name"""
        ProductSubcategory.objects.create(name='Z Subcategory')
        ProductSubcategory.objects.create(name='A Subcategory')
        
        subcategories = ProductSubcategory.objects.all()
        names = [sub.name for sub in subcategories]
        self.assertEqual(names, ['A Subcategory', 'Z Subcategory'])


class ProductModelTests(TestCase):
    """Test cases for Product model"""
    
    def setUp(self):
        self.product_data = {
            'name': 'Test Product',
            'expected_tat': 30,
            'is_active': True
        }
    
    def test_create_product(self):
        """Test creating a product"""
        product = Product.objects.create(**self.product_data)
        
        self.assertEqual(product.name, 'Test Product')
        self.assertEqual(product.expected_tat, 30)
        self.assertTrue(product.is_active)
        self.assertIsInstance(product.id, uuid.UUID)
    
    def test_product_str_representation(self):
        """Test string representation"""
        product = Product.objects.create(**self.product_data)
        self.assertEqual(str(product), 'Test Product')
    
    def test_product_name_uniqueness(self):
        """Test that product names must be unique"""
        Product.objects.create(**self.product_data)
        
        with self.assertRaises(IntegrityError):
            Product.objects.create(**self.product_data)
    
    def test_product_expected_tat_validation(self):
        """Test expected_tat validation"""
        # Test minimum value validation
        product = Product(name='Test Product', expected_tat=0)
        with self.assertRaises(ValidationError):
            product.full_clean()


class ProjectStatusOptionModelTests(TestCase):
    """Test cases for ProjectStatusOption model"""
    
    def setUp(self):
        self.status_data = {
            'name': 'Test Status',
            'category_one': 'Test Category 1',
            'category_two': 'Test Category 2',
            'order': 1,
            'is_active': True
        }
    
    def test_create_status_option(self):
        """Test creating a project status option"""
        status = ProjectStatusOption.objects.create(**self.status_data)
        
        self.assertEqual(status.name, 'Test Status')
        self.assertEqual(status.category_one, 'Test Category 1')
        self.assertEqual(status.category_two, 'Test Category 2')
        self.assertEqual(status.order, 1)
        self.assertTrue(status.is_active)
    
    def test_status_str_representation(self):
        """Test string representation"""
        status = ProjectStatusOption.objects.create(**self.status_data)
        expected = "Test Status (Test Category 1 - Test Category 2)"
        self.assertEqual(str(status), expected)
    
    def test_status_ordering(self):
        """Test status ordering by order field"""
        ProjectStatusOption.objects.create(name='Status 3', order=3, 
                                         category_one='Cat1', category_two='Cat2')
        ProjectStatusOption.objects.create(name='Status 1', order=1,
                                         category_one='Cat1', category_two='Cat2')
        ProjectStatusOption.objects.create(name='Status 2', order=2,
                                         category_one='Cat1', category_two='Cat2')
        
        statuses = ProjectStatusOption.objects.all()
        names = [status.name for status in statuses]
        self.assertEqual(names, ['Status 1', 'Status 2', 'Status 3'])


class ProjectModelTests(TestCase):
    """Test cases for Project model"""
    
    def setUp(self):
        # Create required dependencies
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='DPM'
        )
        
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.subcategory = ProductSubcategory.objects.create(name='Test Subcategory')
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1',
            category_two='Category 2',
            order=1
        )
        
        self.project_data = {
            'opportunity_id': 'OPP001',
            'project_name': 'Test Project',
            'builder_name': 'Test Builder',
            'city': self.city,
            'product': self.product,
            'product_subcategory': self.subcategory,
            'quantity': 1,
            'purchase_date': date.today(),
            'sales_confirmation_date': date.today(),
            'expected_tat': 30,
            'account_manager': 'Test Manager',
            'dpm': self.user,
            'current_status': self.status
        }
    
    def test_create_project(self):
        """Test creating a project"""
        project = Project.objects.create(**self.project_data)
        
        self.assertEqual(project.opportunity_id, 'OPP001')
        self.assertEqual(project.project_name, 'Test Project')
        self.assertEqual(project.builder_name, 'Test Builder')
        self.assertEqual(project.quantity, 1)
        self.assertIsNotNone(project.hs_id)
        self.assertIsInstance(project.id, uuid.UUID)
    
    def test_project_str_representation(self):
        """Test string representation"""
        project = Project.objects.create(**self.project_data)
        expected = "Test Project (OPP001)"
        self.assertEqual(str(project), expected)
    
    def test_project_hs_id_generation(self):
        """Test HS ID generation"""
        # Test that generate_hs_id method works correctly
        hs_id_direct = Project.generate_hs_id()
        self.assertEqual(hs_id_direct, 'A1')
        
        # Create first project manually to test sequence
        project_data1 = self.project_data.copy()
        project1 = Project(**project_data1)
        project1.hs_id = 'A1'
        project1.save()
        self.assertEqual(project1.hs_id, 'A1')
        
        # Test that next generated ID is A2
        hs_id_with_existing = Project.generate_hs_id()
        self.assertEqual(hs_id_with_existing, 'A2')
        
        # Test automatic HS ID generation through save method
        project_data2 = self.project_data.copy()
        project_data2['opportunity_id'] = 'OPP002'
        project_data2['project_name'] = 'Test Project 2'
        project2 = Project(**project_data2)
        project2.save()
        self.assertEqual(project2.hs_id, 'A2')
        
        # Test automatic HS ID generation through objects.create
        project_data3 = self.project_data.copy()
        project_data3['opportunity_id'] = 'OPP003'
        project_data3['project_name'] = 'Test Project 3'
        project3 = Project.objects.create(**project_data3)
        self.assertEqual(project3.hs_id, 'A3')
        
        # Verify all projects have unique HS IDs
        all_projects = Project.objects.all()
        hs_ids = [p.hs_id for p in all_projects]
        self.assertEqual(len(hs_ids), len(set(hs_ids)))  # All unique
        self.assertIn('A1', hs_ids)
        self.assertIn('A2', hs_ids)
        self.assertIn('A3', hs_ids)
    
    def test_project_is_delivered_property(self):
        """Test is_delivered property"""
        # Create delivered status
        delivered_status = ProjectStatusOption.objects.create(
            name='Final Delivery',
            category_one='Delivered',
            category_two='Complete',
            order=10
        )
        
        project = Project.objects.create(**self.project_data)
        self.assertFalse(project.is_delivered)
        
        # Change to delivered status
        project.current_status = delivered_status
        project.save()
        self.assertTrue(project.is_delivered)
    
    def test_project_is_pipeline_property(self):
        """Test is_pipeline property"""
        project = Project.objects.create(**self.project_data)
        self.assertTrue(project.is_pipeline)
        
        # Create delivered status and change to it
        delivered_status = ProjectStatusOption.objects.create(
            name='Final Delivery',
            category_one='Delivered',
            category_two='Complete',
            order=10
        )
        project.current_status = delivered_status
        project.save()
        self.assertFalse(project.is_pipeline)
    
    def test_project_save_creates_status_history(self):
        """Test that saving a project creates status history"""
        project = Project.objects.create(**self.project_data)
        
        # Check that status history was created
        history = ProjectStatusHistory.objects.filter(project=project)
        self.assertEqual(history.count(), 1)
        
        history_entry = history.first()
        self.assertEqual(history_entry.status, self.status)
        self.assertEqual(history_entry.changed_by, self.user)


class ProjectTaskModelTests(TestCase):
    """Test cases for ProjectTask model"""
    
    def setUp(self):
        # Create dependencies
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123',
            role='DPM'
        )
        
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1',
            category_two='Category 2', 
            order=1
        )
        
        self.project = Project.objects.create(
            opportunity_id='OPP001',
            project_name='Test Project',
            builder_name='Test Builder',
            city=self.city,
            product=self.product,
            quantity=1,
            purchase_date=date.today(),
            sales_confirmation_date=date.today(),
            expected_tat=30,
            account_manager='Test Manager',
            dpm=self.user,
            current_status=self.status
        )
        
        self.product_task = ProductTask.objects.create(
            product=self.product,
            name='Test Task',
            description='Test task description'
        )
        
        self.task_data = {
            'project': self.project,
            'product_task': self.product_task,
            'task_type': 'NEW',
            'estimated_time': 120,  # minutes
            'created_by': self.user
        }
    
    def test_create_project_task(self):
        """Test creating a project task"""
        task = ProjectTask.objects.create(**self.task_data)
        
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.product_task, self.product_task)
        self.assertEqual(task.task_type, 'NEW')
        self.assertEqual(task.estimated_time, 120)
        self.assertIsNotNone(task.task_id)
        self.assertTrue(task.task_id.startswith('TID_'))
    
    def test_task_str_representation(self):
        """Test string representation"""
        task = ProjectTask.objects.create(**self.task_data)
        expected = f"{task.task_id} - Test Task (Test Project)"
        self.assertEqual(str(task), expected)
    
    def test_task_id_generation(self):
        """Test task ID generation"""
        task1 = ProjectTask.objects.create(**self.task_data)
        
        task_data2 = self.task_data.copy()
        task2 = ProjectTask.objects.create(**task_data2)
        
        self.assertNotEqual(task1.task_id, task2.task_id)
        self.assertTrue(task1.task_id.startswith('TID_'))
        self.assertTrue(task2.task_id.startswith('TID_'))
    
    def test_get_formatted_time(self):
        """Test get_formatted_time method"""
        task = ProjectTask.objects.create(**self.task_data)
        self.assertEqual(task.get_formatted_time(), "2 hours 0 minutes")
        
        task.estimated_time = 90
        task.save()
        self.assertEqual(task.get_formatted_time(), "1 hour 30 minutes")
    
    def test_get_formatted_hours(self):
        """Test get_formatted_hours method"""
        task = ProjectTask.objects.create(**self.task_data)
        self.assertEqual(task.get_formatted_hours(), "2.0")
        
        task.estimated_time = 90
        task.save()
        self.assertEqual(task.get_formatted_hours(), "1.5")


class TaskAssignmentModelTests(TestCase):
    """Test cases for TaskAssignment model"""
    
    def setUp(self):
        # Create users
        self.dpm = User.objects.create_user(
            username='dpm',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
        
        self.team_member = User.objects.create_user(
            username='teammember',
            email='team@example.com',
            password='testpass123',
            role='TEAM_MEMBER'
        )
        
        # Create other dependencies
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1', 
            category_two='Category 2',
            order=1
        )
        
        self.project = Project.objects.create(
            opportunity_id='OPP001',
            project_name='Test Project',
            builder_name='Test Builder',
            city=self.city,
            product=self.product,
            quantity=1,
            purchase_date=date.today(),
            sales_confirmation_date=date.today(),
            expected_tat=30,
            account_manager='Test Manager',
            dpm=self.dpm,
            current_status=self.status
        )
        
        self.product_task = ProductTask.objects.create(
            product=self.product,
            name='Test Task',
            description='Test task description'
        )
        
        self.project_task = ProjectTask.objects.create(
            project=self.project,
            product_task=self.product_task,
            task_type='NEW',
            estimated_time=120,
            created_by=self.dpm
        )
        
        self.assignment_data = {
            'task': self.project_task,
            'assigned_to': self.team_member,
            'projected_hours': 120,
            'sub_task': 'Test subtask description',
            'rework_type': 'NEW',
            'expected_delivery_date': timezone.now() + timedelta(days=2),
            'assigned_by': self.dpm
        }
    
    def test_create_task_assignment(self):
        """Test creating a task assignment"""
        assignment = TaskAssignment.objects.create(**self.assignment_data)
        
        self.assertEqual(assignment.task, self.project_task)
        self.assertEqual(assignment.assigned_to, self.team_member)
        self.assertEqual(assignment.projected_hours, 120)
        self.assertIsNotNone(assignment.assignment_id)
        self.assertTrue(assignment.assignment_id.startswith('ASID_'))
        self.assertFalse(assignment.is_active)  # Default is False
        self.assertFalse(assignment.is_completed)  # Default is False
    
    def test_assignment_str_representation(self):
        """Test string representation"""
        assignment = TaskAssignment.objects.create(**self.assignment_data)
        expected = f"{assignment.assignment_id} - Test Task -> teammember"
        self.assertEqual(str(assignment), expected)
    
    def test_assignment_id_generation(self):
        """Test assignment ID generation"""
        assignment1 = TaskAssignment.objects.create(**self.assignment_data)
        
        assignment_data2 = self.assignment_data.copy()
        assignment2 = TaskAssignment.objects.create(**assignment_data2)
        
        self.assertNotEqual(assignment1.assignment_id, assignment2.assignment_id)
        self.assertTrue(assignment1.assignment_id.startswith('ASID_'))
        self.assertTrue(assignment2.assignment_id.startswith('ASID_'))
    
    def test_get_formatted_hours(self):
        """Test get_formatted_hours method"""
        assignment = TaskAssignment.objects.create(**self.assignment_data)
        self.assertEqual(assignment.get_formatted_hours(), "2.0")
        
        assignment.projected_hours = 90
        assignment.save()
        self.assertEqual(assignment.get_formatted_hours(), "1.5")
    
    def test_assignment_validation(self):
        """Test assignment validation in clean method"""
        assignment = TaskAssignment(**self.assignment_data)
        
        # Set past delivery date
        assignment.expected_delivery_date = timezone.now() - timedelta(days=1)
        
        with self.assertRaises(ValidationError):
            assignment.clean()


class ProjectServiceTests(TestCase):
    """Test cases for ProjectService"""
    
    def setUp(self):
        # Create test data
        self.dpm = User.objects.create_user(
            username='dpm',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
        
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.subcategory = ProductSubcategory.objects.create(name='Test Subcategory')
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1',
            category_two='Category 2',
            order=1
        )
        
        self.project_data = {
            'opportunity_id': 'OPP001',
            'project_name': 'Test Project',
            'builder_name': 'Test Builder',
            'city': self.city,
            'product': self.product,
            'product_subcategory': self.subcategory,
            'quantity': 1,
            'purchase_date': date.today(),
            'sales_confirmation_date': date.today(),
            'account_manager': 'Test Manager',
            'current_status': self.status
        }
    
    def test_create_project_service(self):
        """Test creating project through service"""
        success, result = ProjectService.create_project(
            project_data=self.project_data,
            user=self.dpm
        )
        
        self.assertTrue(success)
        self.assertIsInstance(result, Project)
        self.assertEqual(result.project_name, 'Test Project')
        self.assertEqual(result.dpm, self.dpm)
        self.assertEqual(result.expected_tat, 30)  # Should default to product TAT
    
    def test_create_project_with_custom_tat(self):
        """Test creating project with custom TAT"""
        project_data = self.project_data.copy()
        project_data['expected_tat'] = 45
        
        success, result = ProjectService.create_project(
            project_data=project_data,
            user=self.dpm
        )
        
        self.assertTrue(success)
        self.assertEqual(result.expected_tat, 45)
    
    def test_get_project_service(self):
        """Test getting project through service"""
        # Create a project first
        success, project = ProjectService.create_project(
            project_data=self.project_data,
            user=self.dpm
        )
        self.assertTrue(success)
        
        # Now get it
        success, retrieved_project = ProjectService.get_project(project.id)
        
        self.assertTrue(success)
        self.assertEqual(retrieved_project.id, project.id)
        self.assertEqual(retrieved_project.project_name, 'Test Project')
    
    def test_get_nonexistent_project(self):
        """Test getting nonexistent project"""
        fake_id = uuid.uuid4()
        success, error = ProjectService.get_project(fake_id)
        
        self.assertFalse(success)
        self.assertEqual(error, "Project not found")
    
    def test_update_project_status_service(self):
        """Test updating project status through service"""
        # Create project
        success, project = ProjectService.create_project(
            project_data=self.project_data,
            user=self.dpm
        )
        self.assertTrue(success)
        
        # Create new status
        new_status = ProjectStatusOption.objects.create(
            name='New Status',
            category_one='New Category 1',
            category_two='New Category 2',
            order=2
        )
        
        # Update status
        success, updated_project = ProjectService.update_project_status(
            project_id=project.id,
            status_id=new_status.id,
            user=self.dpm,
            comments="Test status update"
        )
        
        self.assertTrue(success)
        self.assertEqual(updated_project.current_status, new_status)
        
        # Check that history was created
        history = ProjectStatusHistory.objects.filter(
            project=project,
            status=new_status
        ).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.comments, "Test status update")
    
    def test_update_project_status_same_status(self):
        """Test updating project to same status fails"""
        # Create project
        success, project = ProjectService.create_project(
            project_data=self.project_data,
            user=self.dpm
        )
        self.assertTrue(success)
        
        # Try to update to same status
        success, error = ProjectService.update_project_status(
            project_id=project.id,
            status_id=self.status.id,
            user=self.dpm
        )
        
        self.assertFalse(success)
        self.assertIn("already the current status", error)


class ProjectViewTests(TestCase):
    """Test cases for project views"""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.dpm = User.objects.create_user(
            username='dpm',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
        
        self.team_member = User.objects.create_user(
            username='teammember',
            email='team@example.com',
            password='testpass123',
            role='TEAM_MEMBER'
        )
        
        # Create test data
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1',
            category_two='Category 2',
            order=1
        )
        
        self.project = Project.objects.create(
            opportunity_id='OPP001',
            project_name='Test Project',
            builder_name='Test Builder',
            city=self.city,
            product=self.product,
            quantity=1,
            purchase_date=date.today(),
            sales_confirmation_date=date.today(),
            expected_tat=30,
            account_manager='Test Manager',
            dpm=self.dpm,
            current_status=self.status
        )
    
    def test_project_list_requires_login(self):
        """Test that project list requires login"""
        response = self.client.get(reverse('projects:project_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_project_list_authenticated(self):
        """Test project list for authenticated user"""
        self.client.login(username='dpm', password='testpass123')
        response = self.client.get(reverse('projects:project_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
    
    def test_project_detail_requires_login(self):
        """Test that project detail requires login"""
        response = self.client.get(
            reverse('projects:project_detail', args=[self.project.id])
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_project_detail_authenticated(self):
        """Test project detail for authenticated user"""
        self.client.login(username='dpm', password='testpass123')
        response = self.client.get(
            reverse('projects:project_detail', args=[self.project.id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
        self.assertContains(response, 'Test Builder')
    
    def test_create_project_requires_login(self):
        """Test that create project requires login"""
        response = self.client.get(reverse('projects:create_project'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_create_project_get(self):
        """Test GET request to create project"""
        self.client.login(username='dpm', password='testpass123')
        response = self.client.get(reverse('projects:create_project'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Project')
    
    def test_create_project_post_valid(self):
        """Test POST request to create project with valid data"""
        self.client.login(username='dpm', password='testpass123')
        
        data = {
            'opportunity_id': 'OPP002',
            'project_name': 'New Test Project',
            'builder_name': 'New Builder',
            'city': self.city.id,
            'product': self.product.id,
            'quantity': 2,
            'purchase_date': date.today().isoformat(),
            'sales_confirmation_date': date.today().isoformat(),
            'account_manager': 'New Manager',
            'current_status': self.status.id
        }
        
        response = self.client.post(reverse('projects:create_project'), data)
        
        # Should redirect to project detail on success
        self.assertEqual(response.status_code, 302)
        
        # Check project was created
        project = Project.objects.filter(opportunity_id='OPP002').first()
        self.assertIsNotNone(project)
        self.assertEqual(project.project_name, 'New Test Project')
    
    def test_dpm_task_dashboard_requires_login(self):
        """Test that DPM task dashboard requires login"""
        response = self.client.get(reverse('projects:dpm_task_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_team_member_dashboard_requires_login(self):
        """Test that team member dashboard requires login"""
        response = self.client.get(reverse('projects:team_member_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_team_member_dashboard_authenticated(self):
        """Test team member dashboard for authenticated user"""
        self.client.login(username='teammember', password='testpass123')
        response = self.client.get(reverse('projects:team_member_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        # Should contain dashboard elements
        self.assertContains(response, 'Dashboard')


class ProjectFormTests(TestCase):
    """Test cases for project forms"""
    
    def setUp(self):
        # Create test data
        self.dpm = User.objects.create_user(
            username='dpm',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
        
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.subcategory = ProductSubcategory.objects.create(name='Test Subcategory')
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1',
            category_two='Category 2',
            order=1
        )
    
    def test_project_create_form_valid(self):
        """Test ProjectCreateForm with valid data"""
        form_data = {
            'opportunity_id': 'OPP001',
            'project_name': 'Test Project',
            'builder_name': 'Test Builder',
            'city': self.city.id,
            'product': self.product.id,
            'product_subcategory': self.subcategory.id,
            'quantity': 1,
            'purchase_date': date.today(),
            'sales_confirmation_date': date.today(),
            'account_manager': 'Test Manager',
            'current_status': self.status.id
        }
        
        form = ProjectCreateForm(data=form_data, user=self.dpm)
        self.assertTrue(form.is_valid())
    
    def test_project_create_form_invalid_dates(self):
        """Test ProjectCreateForm with invalid date relationship"""
        form_data = {
            'opportunity_id': 'OPP001',
            'project_name': 'Test Project',
            'builder_name': 'Test Builder',
            'city': self.city.id,
            'product': self.product.id,
            'quantity': 1,
            'purchase_date': date.today() + timedelta(days=1),  # After sales date
            'sales_confirmation_date': date.today(),
            'account_manager': 'Test Manager',
            'current_status': self.status.id
        }
        
        form = ProjectCreateForm(data=form_data, user=self.dpm)
        self.assertFalse(form.is_valid())
        self.assertIn('purchase_date', form.errors)
    
    def test_project_status_update_form_valid(self):
        """Test ProjectStatusUpdateForm with valid data"""
        form_data = {
            'status': self.status.id,
            'comments': 'Test status update comment'
        }
        
        form = ProjectStatusUpdateForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_project_filter_form(self):
        """Test ProjectFilterForm"""
        form_data = {
            'search': 'test',
            'status': self.status.id,
            'product': self.product.id,
            'region': self.region.id,
            'city': self.city.id
        }
        
        form = ProjectFilterForm(data=form_data)
        # Filter form should be valid even with empty data
        self.assertTrue(form.is_valid())


class TimeTrackingModelTests(TestCase):
    """Test cases for time tracking models"""
    
    def setUp(self):
        # Create users
        self.dpm = User.objects.create_user(
            username='dpm',
            email='dpm@example.com',
            password='testpass123',
            role='DPM'
        )
        
        self.team_member = User.objects.create_user(
            username='teammember',
            email='team@example.com',
            password='testpass123',
            role='TEAM_MEMBER'
        )
        
        # Create project and task
        self.region = Region.objects.create(name='Test Region')
        self.city = City.objects.create(name='Test City', region=self.region)
        self.product = Product.objects.create(name='Test Product', expected_tat=30)
        self.status = ProjectStatusOption.objects.create(
            name='Test Status',
            category_one='Category 1',
            category_two='Category 2',
            order=1
        )
        
        self.project = Project.objects.create(
            opportunity_id='OPP001',
            project_name='Test Project',
            builder_name='Test Builder',
            city=self.city,
            product=self.product,
            quantity=1,
            purchase_date=date.today(),
            sales_confirmation_date=date.today(),
            expected_tat=30,
            account_manager='Test Manager',
            dpm=self.dpm,
            current_status=self.status
        )
        
        self.product_task = ProductTask.objects.create(
            product=self.product,
            name='Test Task',
            description='Test task description'
        )
        
        self.project_task = ProjectTask.objects.create(
            project=self.project,
            product_task=self.product_task,
            task_type='NEW',
            estimated_time=120,
            created_by=self.dpm
        )
        
        self.assignment = TaskAssignment.objects.create(
            task=self.project_task,
            assigned_to=self.team_member,
            projected_hours=120,
            sub_task='Test subtask',
            expected_delivery_date=timezone.now() + timedelta(days=2),
            assigned_by=self.dpm
        )
    
    def test_active_timer_creation(self):
        """Test creating an active timer"""
        timer = ActiveTimer.objects.create(
            assignment=self.assignment,
            team_member=self.team_member,
            started_at=timezone.now()
        )
        
        self.assertEqual(timer.assignment, self.assignment)
        self.assertEqual(timer.team_member, self.team_member)
        self.assertIsNotNone(timer.started_at)
    
    def test_active_timer_one_per_user(self):
        """Test that only one active timer per user is allowed"""
        # Create first timer
        ActiveTimer.objects.create(
            assignment=self.assignment,
            team_member=self.team_member,
            started_at=timezone.now()
        )
        
        # Try to create second timer for same user
        with self.assertRaises(IntegrityError):
            ActiveTimer.objects.create(
                assignment=self.assignment,
                team_member=self.team_member,
                started_at=timezone.now()
            )
    
    def test_time_session_creation(self):
        """Test creating a time session"""
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=2)
        
        session = TimeSession.objects.create(
            assignment=self.assignment,
            team_member=self.team_member,
            started_at=start_time,
            ended_at=end_time,
            duration_minutes=120,
            date_worked=date.today(),
            session_type='TIMER'
        )
        
        self.assertEqual(session.assignment, self.assignment)
        self.assertEqual(session.team_member, self.team_member)
        self.assertEqual(session.duration_minutes, 120)
        self.assertEqual(session.session_type, 'TIMER')
    
    def test_daily_time_total_creation(self):
        """Test creating a daily time total"""
        daily_total = DailyTimeTotal.objects.create(
            assignment=self.assignment,
            team_member=self.team_member,
            date_worked=date.today(),
            total_minutes=120
        )
        
        self.assertEqual(daily_total.assignment, self.assignment)
        self.assertEqual(daily_total.team_member, self.team_member)
        self.assertEqual(daily_total.total_minutes, 120)
        self.assertEqual(daily_total.get_hours(), 2)
        self.assertEqual(daily_total.get_minutes(), 0)
        self.assertEqual(daily_total.get_formatted_total(), "2h 0m")
    
    def test_daily_roster_creation(self):
        """Test creating a daily roster entry"""
        roster = DailyRoster.objects.create(
            team_member=self.team_member,
            date=date.today(),
            status='PRESENT',
            misc_hours=30,  # 30 minutes
            misc_description='Team meeting'
        )
        
        self.assertEqual(roster.team_member, self.team_member)
        self.assertEqual(roster.status, 'PRESENT')
        self.assertEqual(roster.misc_hours, 30)
        self.assertEqual(roster.misc_description, 'Team meeting')


class HolidayModelTests(TestCase):
    """Test cases for Holiday model"""
    
    def test_create_holiday(self):
        """Test creating a holiday"""
        holiday = Holiday.objects.create(
            date=date(2024, 12, 25),
            name='Christmas Day',
            location='Gurgaon',
            year=2024
        )
        
        self.assertEqual(holiday.name, 'Christmas Day')
        self.assertEqual(holiday.location, 'Gurgaon')
        self.assertEqual(holiday.year, 2024)
        self.assertTrue(holiday.is_active)
    
    def test_holiday_unique_constraint(self):
        """Test holiday unique constraint (date + location)"""
        Holiday.objects.create(
            date=date(2024, 12, 25),
            name='Christmas Day',
            location='Gurgaon',
            year=2024
        )
        
        # Try to create duplicate
        with self.assertRaises(IntegrityError):
            Holiday.objects.create(
                date=date(2024, 12, 25),
                name='Christmas Day',
                location='Gurgaon',
                year=2024
            )
    
    def test_holiday_different_locations(self):
        """Test that same date can have different locations"""
        Holiday.objects.create(
            date=date(2024, 12, 25),
            name='Christmas Day',
            location='Gurgaon',
            year=2024
        )
        
        # Different location should work
        holiday2 = Holiday.objects.create(
            date=date(2024, 12, 25),
            name='Christmas Day',
            location='Mumbai',
            year=2024
        )
        
        self.assertEqual(holiday2.location, 'Mumbai')


class ReportingServiceTests(TestCase):
    """Test cases for ReportingService"""
    
    def setUp(self):
        # Create test data similar to other tests
        self.team_member = User.objects.create_user(
            username='teammember',
            email='team@example.com',
            password='testpass123',
            role='TEAM_MEMBER'
        )
        
        self.start_date = date.today() - timedelta(days=7)
        self.end_date = date.today()
    
    def test_get_team_member_metrics(self):
        """Test getting team member metrics"""
        metrics = ReportingService.get_team_member_metrics(
            self.team_member,
            self.start_date,
            self.end_date
        )
        
        # Should return a dictionary with expected keys
        expected_keys = [
            'total_assignments', 'completed_assignments', 'total_hours_worked',
            'avg_quality_rating', 'assignments_on_time', 'assignments_late',
            'productivity_score'
        ]
        
        for key in expected_keys:
            self.assertIn(key, metrics)
    
    def test_get_team_overview(self):
        """Test getting team overview"""
        overview = ReportingService.get_team_overview(
            self.start_date,
            self.end_date
        )
        
        # Should return a dictionary with team metrics
        self.assertIsInstance(overview, dict)
        # Should have team member data
        self.assertIn('team_members', overview)


# Run the tests
if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(DEBUG=True)
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['projects.tests'])
