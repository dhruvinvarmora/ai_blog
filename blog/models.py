from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import os
from cloudinary.models import CloudinaryField
# Create your models here.
from django.db import models
from decouple import config
from django.templatetags.static import static

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name

def post_image_path(instance, filename):
    """Generate file path for post images"""
    post_slug = instance.post.slug
    return f'posts/{post_slug}/{filename}'

def post_thumbnail_path(instance, filename):
    """Generate file path for post thumbnails"""
    post_slug = instance.slug
    return f'posts/{post_slug}/thumbnail/{filename}'

def post_featured_path(instance, filename):
    """Generate file path for post featured images"""
    post_slug = instance.slug
    return f'posts/{post_slug}/featured/{filename}'

class PostImage(models.Model):
    IMAGE_TYPES = (
        ('overview', 'Overview'),
        ('care', 'Care'),
        ('closeup', 'Closeup'),
        ('indoor', 'Indoor'),
        ('healthy', 'Healthy'),
        ('decor', 'Decor'),
    )
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image', folder='posts/images/', blank=True, null=True)
    image_url = models.URLField(blank=True,max_length=500)  # Keep for external URLs
    caption = models.TextField(blank=True)
    alt_text = models.TextField(blank=True)
    # order = models.CharField(null=True, blank=True, max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_downloaded = models.BooleanField(default=False)
    image_type = models.CharField(max_length=255, choices=IMAGE_TYPES)

    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.post.title} - Image {self.order}"
    
    @property
    def image_display(self):
        """Return local image if available, otherwise URL"""
        if self.image and self.is_downloaded:
            return self.image.url
        return self.image_url

    @property
    def image_url_or_default(self):
        if self.image_url:
            return self.image_url
        elif self.image:
            return self.image.url
        return static('images/default-plant.jpg')
    
    @property
    def has_image(self):
        return bool(self.image or self.image_url)
class Post(models.Model):
    CATEGORY_CHOICES = [
        ('plants', 'Plants'),
        ('flowers', 'Flowers'),
        ('fruits', 'Fruits'),
        ('gardening', 'Gardening Tips'),
        ('care', 'Plant Care'),
    ]
    
    title = models.TextField()
    slug = models.SlugField(unique=True)
    content = models.TextField()
    summary = models.TextField()
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES, default='plants')
    tags = models.ManyToManyField(Tag, blank=True)
    destination_name = models.TextField(blank=True)
    country = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(default=timezone.now)
    
    # Local image storage
    thumbnail = CloudinaryField('image', folder='posts/thumbnails/', blank=True, null=True)
    featured_image = CloudinaryField('image', folder='posts/featured/', blank=True, null=True)
    
    # Keep URL fields for fallback
    thumbnail_url = models.URLField(blank=True,max_length=500)
    featured_image_url = models.URLField(blank=True,max_length=500)
    video_url = models.URLField(blank=True,max_length=500)
    
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    
    # Plant/Fruit specific fields
    scientific_name = models.TextField(blank=True)
    family = models.TextField(blank=True)
    care_difficulty = models.CharField(max_length=20, choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ], blank=True)
    watering_needs = models.TextField(blank=True)
    sunlight_requirements = models.TextField(blank=True)
    growth_rate = models.TextField(blank=True)
    max_height = models.TextField(blank=True)
    blooming_season = models.TextField(blank=True)
    harvest_time = models.TextField(blank=True,null=True)
    
    class Meta:
        ordering = ['-published_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        if not self.thumbnail and not self.thumbnail_url:
            # Use a default placeholder
            cloudinary_cloud_name = config("CLOUDINARY_CLOUD_NAME", default="demo")
            self.thumbnail_url = f"https://res.cloudinary.com/{cloudinary_cloud_name}/image/upload/v1/plant-placeholder.jpg"
        
        if not self.featured_image and not self.featured_image_url:
            self.featured_image_url = f"https://res.cloudinary.com/{cloudinary_cloud_name}/image/upload/v1/plant-featured-placeholder.jpg"
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog:post_detail', kwargs={'slug': self.slug})
    
    def get_image_by_type(self, image_type):
        """Get the first image of specified type"""
        try:
            return self.images.filter(image_type=image_type).first()
        except:
            return None
    
    def get_image_url_by_type(self, image_type):
        """Get URL for image of specified type"""
        image = self.get_image_by_type(image_type)
        if image:
            return image.image_url if image.image_url else (image.image.url if image.image else None)
        return None
    @property
    def thumbnail_display(self):
        """Return local thumbnail if available, otherwise URL or default"""
        if self.thumbnail:
            return self.thumbnail.url
        elif self.thumbnail_url:
            return self.thumbnail_url
        return static('images/banner-image-6.jpg')
    
    @property
    def main_images(self):
        """Get the main images for the post (excluding thumbnail and featured)"""
        return self.images.filter(order__gte=1).order_by('order')
    
    @property
    def all_images(self):
        """Get all images including thumbnail and featured"""
        images = []
        if self.featured_image_display:
            images.append({
                'url': self.featured_image_display,
                'caption': 'Featured Image',
                'alt_text': f'Featured image of {self.title}',
                'order': 0
            })
        if self.thumbnail_display:
            images.append({
                'url': self.thumbnail_display,
                'caption': 'Thumbnail',
                'alt_text': f'Thumbnail of {self.title}',
                'order': -1
            })
        for img in self.images.all():
            images.append({
                'url': img.image_display,
                'caption': img.caption,
                'alt_text': img.alt_text,
                'order': img.order
            })
        return sorted(images, key=lambda x: x['order'])
    
    def get_images_by_type(self):
        """Get images organized by their type"""
        return {img.image_type: img for img in self.images.all().order_by('order')}
    @property
    def featured_image_display(self):
        """Return local featured image if available, otherwise URL or default"""
        if self.featured_image:
            return self.featured_image.url
        elif self.featured_image_url:
            return self.featured_image_url
        return static('images/contact-us-banner-image.jpg')

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_responded = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
    
    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

class PostScheduler(models.Model):
    last_run = models.DateTimeField(default=timezone.now)
    is_running = models.BooleanField(default=False)
    task_id = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"Scheduler (Last run: {self.last_run}, Running: {self.is_running})"
    
    class Meta:
        verbose_name = "Post Scheduler"
        verbose_name_plural = "Post Scheduler"   