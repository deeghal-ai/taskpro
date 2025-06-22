# projects/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import ProductSubcategory, Product, ProjectStatusOption, Project, ProjectStatusHistory, ProductTask, ProjectTask, TaskAssignment
from .models import ActiveTimer, TimeSession, DailyTimeTotal, TimerActionLog, DailyRoster, Holiday, ProjectDelivery


@admin.register(ProductSubcategory)
class ProductSubcategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Product Subcategories.
    
    Provides a simple interface for managing subcategories with status tracking.
    Metadata fields are kept but hidden from the interface as requested.
    """
    list_display = ('name', 'is_active', 'get_projects_count')
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    # Hide metadata fields but keep them in database
    exclude = ('created_at', 'updated_at')
    
    def get_projects_count(self, obj):
        """Display the number of projects using this subcategory"""
        count = obj.projects.count()
        return format_html(
            '<a href="{}?product_subcategory__id={}">{} projects</a>',
            '../project/',
            obj.id,
            count
        )
    get_projects_count.short_description = 'Projects'


@admin.register(ProjectStatusOption)
class ProjectStatusOptionAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for Project Status Options.
    """
    list_display = (
        'order',          
        'name',           
        'category_one',   
        'category_two',   
        'is_active',      
        'created_at'      
    )
    
    # Specify that 'name' should be the link field
    list_display_links = ('name',)
    
    # Now 'order' can be editable since it's not the link field
    list_editable = (
        'order',          
        'is_active'       
    )
    
    list_filter = (
        'is_active',
        'category_one',   
        'category_two',   
        'created_at'
    )
    
    search_fields = (
        'name',
        'category_one',
        'category_two'
    )
    
    ordering = ['order', 'name']
    
    list_per_page = 100  # Temporarily increased to show all records
    
    fieldsets = (
        ('Status Information', {
            'fields': (
                'name',
                'order',
                'is_active'
            )
        }),
        ('Categories', {
            'fields': (
                'category_one',
                'category_two'
            )
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automated timestamps for record keeping'
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # If editing an existing object
            return self.readonly_fields + ('name',)
        return self.readonly_fields
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add debug info"""
        from django.contrib import messages
        extra_context = extra_context or {}
        
        total_count = ProjectStatusOption.objects.count()
        active_count = ProjectStatusOption.objects.filter(is_active=True).count()
        
        # Add message to admin interface
        messages.info(request, f"DEBUG: Database has {total_count} total status options ({active_count} active)")
        
        extra_context['total_count'] = total_count
        extra_context['active_count'] = active_count
        
        print(f"DEBUG: Total ProjectStatusOption count: {total_count}")
        print(f"DEBUG: Active ProjectStatusOption count: {active_count}")
        
        return super().changelist_view(request, extra_context)


@admin.register(ProjectStatusHistory)
class ProjectStatusHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Project Status History.
    
    This interface provides a comprehensive view of all status changes,
    making it easy to track project progression and audit status changes.
    """
    list_display = (
        'project',
        'status',
        'category_one_snapshot',
        'category_two_snapshot',
        'changed_by',
        'changed_at'
    )
    
    list_filter = (
        'status',
        'category_one_snapshot',
        'category_two_snapshot',
        'changed_by',
        'changed_at'
    )
    
    search_fields = (
        'project__project_name',
        'project__opportunity_id',
        'status__name',
        'comments'
    )
    
    readonly_fields = ('changed_at', 'category_one_snapshot', 'category_two_snapshot')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Admin interface for Projects that provides comprehensive management capabilities.
    The interface is organized to make project management efficient for DPMs.
    """

    def view_details_link(self, obj):
        """Adds a link to the custom detail view for each project"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('projects:project_detail', args=[obj.id])
        return format_html('<a href="{}">View Details</a>', url)
    
    view_details_link.short_description = 'Details'  # Column header in admin

    list_display = (
        'hs_id',
        'project_name',
        'opportunity_id',
        'project_type',
        'builder_name',
        'city',
        'product',
        'get_status_display',
        'dpm',
        'project_incharge',
        'expected_tat',
        'expected_completion_date',
        'purchase_date',
        'view_details_link',
    )
    
    list_filter = (
        'project_type',
        'current_status',
        'city__region',
        'city',
        'product',
        'product_subcategory',
        'dpm',
        'project_incharge', 
        ('project_incharge', admin.EmptyFieldListFilter),
    )
    
    search_fields = (
        'project_name',
        'opportunity_id',
        'builder_name',
        'account_manager',
        'product__name',
        'current_status__name',
        'dpm__username',
        'dpm__first_name',
        'dpm__last_name',
        'project_incharge__username',
        'project_incharge__first_name',
        'project_incharge__last_name',
    )
    
    readonly_fields = ('hs_id','created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'hs_id',
                'opportunity_id',
                'project_type',
                'project_name',
                'builder_name',
                'city'
            )
        }),
        ('Product Information', {
            'fields': (
                'product',
                'product_subcategory',
                'package_id',
                'quantity'
            )
        }),
        ('Important Dates', {
            'fields': (
                'purchase_date',
                'sales_confirmation_date',
                'expected_tat',
                'expected_completion_date',
            )
        }),
        ('Team Assignment', {
            'fields': (
                'account_manager',
                'dpm',
                'project_incharge',
                'delivery_performance_rating',
            )
        }),
        ('Status Information', {
            'fields': (
                'current_status',
            )
        }),
        ('System Information', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_status_display(self, obj):
        """
        Displays the status with its categories in a readable format.
        This helps DPMs quickly understand the current state of a project.
        """
        if obj.current_status:
            return f"{obj.current_status.name} ({obj.current_status.category_one} - {obj.current_status.category_two})"
        return "-"
    get_status_display.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        """
        Handles project saving with proper user assignment and status tracking.
        This ensures all project changes are properly recorded.
        """
        obj._current_user = request.user
        if 'current_status' in form.changed_data:
            obj._status_change_comment = request.POST.get('status_change_comment', '')
        super().save_model(request, obj, form, change)
    
    class Media:
        """
        Add any custom CSS/JS needed for the admin interface
        """
        css = {
            'all': ('admin/css/project_admin.css',)  # You'll need to create this CSS file
        }


@admin.register(ProductTask)
class ProductTaskAdmin(admin.ModelAdmin):
    """Admin interface for managing product-specific tasks."""
    list_display = ('name', 'product', 'is_active', 'created_at')
    list_filter = ('product', 'is_active')
    search_fields = ('name', 'product__name', 'description')
    ordering = ('product', 'name')


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    """Admin interface for managing project tasks."""
    list_display = (
        'task_id',
        'project',
        'product_task',
        'task_type',
        'estimated_time',
        'total_projected_hours',
        'created_by',
        'created_at'
    )
    list_filter = (
        'task_type',
        'created_by',
        'created_at'
    )
    search_fields = (
        'task_id',
        'project__project_name',
        'project__hs_id',
        'product_task__name'
    )
    readonly_fields = ('task_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        """Optimize query by selecting related fields."""
        return super().get_queryset(request).select_related(
            'project',
            'product_task',
            'created_by'
        )



@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for managing task assignments."""
    list_display = (
        'assignment_id',
        'task',
        'assigned_to',
        'assigned_date',
        'projected_hours',
        'is_completed',
        'expected_delivery_date',
        'quality_rating'
    )
    list_filter = (
        'is_completed',
        'assigned_date',
        'rework_type',
        'assigned_by'
    )
    search_fields = (
        'assignment_id',
        'task__task_id',
        'assigned_to__username',
        'assigned_to__first_name',
        'assigned_to__last_name',
        'sub_task'
    )
    readonly_fields = ('assignment_id', 'assigned_date', 'created_at', 'updated_at')
    ordering = ('-assigned_date',)

    def get_queryset(self, request):
        """Optimize query by selecting related fields."""
        qs = super().get_queryset(request).select_related(
            'task',
            'assigned_to',
            'assigned_by'
        )
        return qs


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Products.
    
    Shows essential product information and provides quick access to related projects.
    TAT is prominently displayed as it's a key project planning metric.
    """
    list_display = (
        'name',
        'expected_tat',
        'is_active',
        'get_projects_count'
    )
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    # Hide metadata fields
    exclude = ('created_at', 'updated_at')
    
    # Organize fields into logical groups
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'expected_tat', 'is_active')
        }),
    )
    
    def get_projects_count(self, obj):
        """Display number of projects using this product with a link to filtered view"""
        count = obj.projects.count()
        return format_html(
            '<a href="{}?product__id={}">{} projects</a>',
            '../project/',
            obj.id,
            count
        )
    get_projects_count

@admin.register(ActiveTimer)
class ActiveTimerAdmin(admin.ModelAdmin):
    list_display = ('team_member', 'assignment', 'started_at', 'last_updated')
    list_filter = ('started_at', 'team_member')
    readonly_fields = ('last_updated',)

@admin.register(TimeSession)
class TimeSessionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'team_member', 'date_worked', 'get_formatted_duration', 'session_type')
    list_filter = ('date_worked', 'session_type', 'team_member')
    readonly_fields = ('created_at',)

@admin.register(DailyTimeTotal)
class DailyTimeTotalAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'team_member', 'date_worked', 'get_formatted_total', 'is_manually_edited')
    list_filter = ('date_worked', 'is_manually_edited', 'team_member')
    readonly_fields = ('last_updated',)

@admin.register(TimerActionLog)
class TimerActionLogAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'team_member', 'action', 'timestamp')
    list_filter = ('action', 'timestamp', 'team_member')
    readonly_fields = ('timestamp',)

@admin.register(DailyRoster)
class DailyRosterAdmin(admin.ModelAdmin):
    list_display = ('team_member', 'date', 'status', 'get_total_hours_formatted', 'is_auto_created')
    list_filter = ('status', 'date', 'is_auto_created', 'team_member')
    search_fields = ('team_member__username', 'team_member__first_name', 'team_member__last_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-date', 'team_member')


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'location', 'year', 'is_active')
    list_filter = ('year', 'location', 'is_active')
    search_fields = ('name', 'location')
    ordering = ('date',)

@admin.register(ProjectDelivery)
class ProjectDeliveryAdmin(admin.ModelAdmin):
    """Admin interface for tracking project deliveries and performance ratings."""
    list_display = (
        'hs_id',
        'project_name',
        'project_incharge', 
        'delivery_date',
        'delivery_performance_rating',
        'days_variance',
        'actual_completion_date'
    )
    list_filter = (
        'delivery_date',
        'delivery_performance_rating',
        'project_incharge'
    )
    search_fields = (
        'hs_id',
        'project_name',
        'project_incharge__username',
        'project_incharge__first_name',
        'project_incharge__last_name'
    )
    readonly_fields = ('created_at', 'days_variance')
    ordering = ('-delivery_date',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project', 'project_incharge')