from django.contrib import admin
from django.utils.html import format_html
from .models import (
    VideoProduct, VideoProject, VideoProjectStatusOption,
    VideoProjectStatusHistory, VideoProjectDelivery
)

@admin.register(VideoProduct)
class VideoProductAdmin(admin.ModelAdmin):
    """
    Video Product admin - mirrors Product admin from projects app.
    """
    list_display = ('name', 'expected_tat', 'is_active', 'get_projects_count')
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
        """Display number of video projects using this product with a link to filtered view"""
        count = obj.video_projects.count()
        return format_html(
            '<a href="{}?product__id={}">{} projects</a>',
            '../videoproject/',
            obj.id,
            count
        )
    get_projects_count.short_description = 'Projects'

@admin.register(VideoProjectStatusOption)
class VideoProjectStatusOptionAdmin(admin.ModelAdmin):
    """
    Video Project Status Option admin - mirrors ProjectStatusOption admin from projects app.
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
    
    list_per_page = 100
    
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

class VideoProjectStatusHistoryInline(admin.TabularInline):
    model = VideoProjectStatusHistory
    extra = 0
    readonly_fields = ['changed_at', 'changed_by', 'category_one_snapshot', 'category_two_snapshot']
    fields = ['status', 'changed_by', 'changed_at', 'comments']
    ordering = ['-changed_at']

@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    """
    Video Project admin - mirrors Project admin from projects app.
    """

    def view_details_link(self, obj):
        """Adds a link to the custom detail view for each video project"""
        from django.urls import reverse
        from django.utils.html import format_html
        
        url = reverse('video_production:project_detail', args=[obj.id])
        return format_html('<a href="{}">View Details</a>', url)
    
    view_details_link.short_description = 'Details'

    list_display = (
        'hs_id',
        'project_name',
        'builder_name',
        'city',
        'product',
        'quantity',
        'get_status_display',
        'video_pm',
        'expected_tat',
        'purchase_date',
        'view_details_link',
    )
    
    list_filter = (
        'project_type',
        'current_status',
        'city__region',
        'city',
        'product',
        'video_pm',
    )
    
    search_fields = (
        'project_name',
        'opportunity_id',
        'builder_name',
        'account_manager',
        'product__name',
        'current_status__name',
        'video_pm__username',
        'video_pm__first_name',
        'video_pm__last_name',
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
                'city',
                'product',
                'package_id',
                'quantity',
                'purchase_date',
                'sales_confirmation_date',
                'expected_tat',
            )
        }),
        ('Team Assignment', {
            'fields': (
                'account_manager',
                'video_pm',
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

    inlines = [VideoProjectStatusHistoryInline]

    def get_status_display(self, obj):
        """
        Displays the status with its categories in a readable format.
        """
        if obj.current_status:
            return f"{obj.current_status.name} ({obj.current_status.category_one} - {obj.current_status.category_two})"
        return "-"
    get_status_display.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        """
        Handles video project saving with proper user assignment and status tracking.
        """
        obj._current_user = request.user
        if 'current_status' in form.changed_data:
            obj._status_change_comment = request.POST.get('status_change_comment', '')
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Optimize query with related objects"""
        return super().get_queryset(request).select_related(
            'video_pm', 'current_status', 'product', 'city'
        )

@admin.register(VideoProjectStatusHistory)
class VideoProjectStatusHistoryAdmin(admin.ModelAdmin):
    """
    Video Project Status History admin - mirrors ProjectStatusHistory admin from projects app.
    """
    def get_hs_id(self, obj):
        """Display the HS ID from the related project"""
        return obj.project.hs_id if obj.project else '-'
    get_hs_id.short_description = 'HS ID'
    get_hs_id.admin_order_field = 'project__hs_id'

    list_display = (
        'project',
        'get_hs_id',
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
    
    readonly_fields = ('category_one_snapshot', 'category_two_snapshot')
    ordering = ['-changed_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'project', 'status', 'changed_by'
        )

@admin.register(VideoProjectDelivery)
class VideoProjectDeliveryAdmin(admin.ModelAdmin):
    """
    Video Project Delivery admin - mirrors ProjectDelivery admin from projects app.
    """
    list_display = (
        'hs_id',
        'project_name',
        'delivery_date',
        'days_variance',
        'actual_completion_date'
    )
    list_filter = (
        'delivery_date',
    )
    search_fields = (
        'hs_id',
        'project_name',
    )
    readonly_fields = ('created_at', 'days_variance')
    ordering = ('-delivery_date',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')

# Customize admin site
admin.site.site_header = 'Housing Studio - Video Production Admin'
admin.site.site_title = 'Video Production Admin'
admin.site.index_title = 'Video Production Management'
