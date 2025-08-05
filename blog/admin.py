from django.contrib import admin
from .models import Post, Category, Tag, PostImage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1
    fields = ['image_url', 'caption', 'alt_text', 'order']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'is_published', 'is_featured', 
        'published_at', 'view_count', 'care_difficulty'
    ]
    list_filter = [
        'category', 'is_published', 'is_featured', 'care_difficulty',
        'published_at', 'created_at'
    ]
    search_fields = ['title', 'content', 'summary', 'scientific_name']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at', 'view_count']
    filter_horizontal = ['tags']
    inlines = [PostImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'content', 'summary', 'category')
        }),
        ('Plant Details', {
            'fields': (
                'scientific_name', 'family', 'care_difficulty', 
                'watering_needs', 'sunlight_requirements', 'growth_rate',
                'max_height', 'blooming_season', 'harvest_time'
            ),
            'classes': ('collapse',)
        }),
        ('Media & Links', {
            'fields': ('thumbnail_url', 'featured_image_url', 'video_url')
        }),
        ('SEO & Publishing', {
            'fields': ('tags', 'is_published', 'is_featured', 'published_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'view_count'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_published', 'make_unpublished', 'make_featured', 'make_unfeatured']
    
    def make_published(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} posts were successfully marked as published.')
    make_published.short_description = "Mark selected posts as published"
    
    def make_unpublished(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} posts were successfully marked as unpublished.')
    make_unpublished.short_description = "Mark selected posts as unpublished"
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} posts were successfully marked as featured.')
    make_featured.short_description = "Mark selected posts as featured"
    
    def make_unfeatured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} posts were successfully marked as unfeatured.')
    make_unfeatured.short_description = "Mark selected posts as unfeatured"

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ['post', 'order', 'caption', 'image_url']
    list_filter = ['post__category']
    search_fields = ['post__title', 'caption']
    ordering = ['post', 'order']
