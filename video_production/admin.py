from django.contrib import admin
from .models import (
    VideoProduct, VideoProject, VideoProjectStatusOption, VideoCut, 
    VoiceoverScript, VideoProjectStatusHistory, VideoProjectDelivery
)

@admin.register(VideoProduct)
class VideoProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'typical_cut_rounds', 'requires_voiceover', 'expected_tat', 'is_active']
    list_filter = ['requires_voiceover', 'is_active']
    search_fields = ['name']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Production Details', {
            'fields': ('typical_cut_rounds', 'requires_voiceover', 'expected_tat')
        }),
    )

@admin.register(VideoProjectStatusOption)
class VideoProjectStatusOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    ordering = ['order']
    
    fieldsets = (
        ('Status Information', {
            'fields': ('name', 'category', 'order')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )

class VideoCutInline(admin.TabularInline):
    model = VideoCut
    extra = 0
    readonly_fields = ['delivered_date', 'feedback_received_date']
    fields = ['cut_number', 'status', 'delivered_date', 'rework_required', 'client_feedback', 'feedback_received_date']

class VoiceoverScriptInline(admin.TabularInline):
    model = VoiceoverScript
    extra = 0
    readonly_fields = ['shared_date', 'approved_date']
    fields = ['script_version', 'status', 'shared_date', 'approved_date']

class VideoProjectStatusHistoryInline(admin.TabularInline):
    model = VideoProjectStatusHistory
    extra = 0
    readonly_fields = ['changed_at', 'changed_by']
    fields = ['status', 'changed_by', 'changed_at', 'comments']
    ordering = ['-changed_at']

@admin.register(VideoProject)
class VideoProjectAdmin(admin.ModelAdmin):
    list_display = [
        'hs_id', 'project_name', 'video_pm', 'current_status', 'video_product',
        'current_cut_number', 'voiceover_status', 'created_at'
    ]
    list_filter = [
        'current_status', 'video_pm', 'city', 'video_product', 
        'voiceover_required', 'voiceover_status', 'created_at'
    ]
    search_fields = ['hs_id', 'project_name', 'builder_name', 'opportunity_id']
    readonly_fields = ['hs_id', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Project Identification', {
            'fields': ('hs_id', 'opportunity_id', 'project_name', 'builder_name')
        }),
        ('Project Details', {
            'fields': ('city', 'video_product', 'quantity', 'production_vendor')
        }),
        ('Video Production', {
            'fields': ('shoot_location', 'shoot_date', 'video_duration_minutes')
        }),
        ('Timeline', {
            'fields': ('purchase_date', 'expected_completion_date', 'actual_delivery_date')
        }),
        ('Cut Management', {
            'fields': ('current_cut_number', 'max_cuts_allowed')
        }),
        ('Voiceover', {
            'fields': ('voiceover_required', 'voiceover_status')
        }),
        ('Assignment & Status', {
            'fields': ('video_pm', 'current_status')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [VideoCutInline, VoiceoverScriptInline, VideoProjectStatusHistoryInline]
    
    def get_queryset(self, request):
        """Optimize query with related objects"""
        return super().get_queryset(request).select_related(
            'video_pm', 'current_status', 'video_product', 'city'
        )

@admin.register(VideoCut)
class VideoCutAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'cut_number', 'status', 'delivered_date', 
        'rework_required', 'feedback_received_date'
    ]
    list_filter = ['status', 'rework_required', 'delivered_date']
    search_fields = ['project__hs_id', 'project__project_name', 'client_feedback']
    readonly_fields = ['delivered_date', 'feedback_received_date']
    ordering = ['project', 'cut_number']
    
    fieldsets = (
        ('Cut Information', {
            'fields': ('project', 'cut_number', 'status')
        }),
        ('Delivery', {
            'fields': ('delivered_date', 'rework_required')
        }),
        ('Feedback', {
            'fields': ('client_feedback', 'feedback_received_date')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')

@admin.register(VoiceoverScript)
class VoiceoverScriptAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'script_version', 'status', 'shared_date', 'approved_date'
    ]
    list_filter = ['status', 'shared_date', 'approved_date']
    search_fields = ['project__hs_id', 'project__project_name', 'script_content']
    readonly_fields = ['shared_date', 'approved_date']
    ordering = ['project', 'script_version']
    
    fieldsets = (
        ('Script Information', {
            'fields': ('project', 'script_version', 'status')
        }),
        ('Timeline', {
            'fields': ('shared_date', 'approved_date')
        }),
        ('Content', {
            'fields': ('script_content',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')

@admin.register(VideoProjectStatusHistory)
class VideoProjectStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['project', 'status', 'changed_by', 'changed_at']
    list_filter = ['status', 'changed_by', 'changed_at']
    search_fields = ['project__hs_id', 'project__project_name', 'comments']
    readonly_fields = ['changed_at']
    ordering = ['-changed_at']
    
    fieldsets = (
        ('Status Change', {
            'fields': ('project', 'status', 'changed_by', 'changed_at')
        }),
        ('Details', {
            'fields': ('comments',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'project', 'status', 'changed_by'
        )

@admin.register(VideoProjectDelivery)
class VideoProjectDeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'delivery_performance_rating', 'delivery_date', 
        'days_variance', 'total_cuts_delivered', 'voiceover_iterations'
    ]
    list_filter = ['delivery_performance_rating', 'delivery_date']
    search_fields = ['project__hs_id', 'project__project_name']
    readonly_fields = ['created_at']
    ordering = ['-delivery_date']
    
    fieldsets = (
        ('Project', {
            'fields': ('project',)
        }),
        ('Delivery Performance', {
            'fields': ('delivery_performance_rating', 'delivery_date', 'days_variance')
        }),
        ('Production Metrics', {
            'fields': ('total_cuts_delivered', 'voiceover_iterations')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')

# Customize admin site
admin.site.site_header = 'Housing Studio - Video Production Admin'
admin.site.site_title = 'Video Production Admin'
admin.site.index_title = 'Video Production Management'
