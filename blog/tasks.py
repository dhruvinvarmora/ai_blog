from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.utils import timezone
from blog.models import Post, PostScheduler
import logging
from datetime import timedelta
from blog.management.commands.generate_post import Command
logger = get_task_logger(__name__)

@shared_task(bind=True, name="blog.tasks.generate_blog_post")
def generate_blog_post(self, category=None, force=False):
    """
    Celery task to generate blog posts with retry functionality
    """
    try:
        logger.info(f"🚀 Starting blog post generation for category: {category or 'auto'}")
        
        # Update scheduler status
        scheduler = PostScheduler.objects.get_or_create(pk=1)[0]
        scheduler.is_running = True
        scheduler.task_id = self.request.id
        scheduler.save()
        
        # Call the command with all required parameters
        cmd = Command()
        cmd.handle(
            category=category,
            force=force,
            task_id=self.request.id,
            verbose=False  # Explicitly set verbose
        )
        
        # Verify the post was created
        latest_post = Post.objects.filter(
            published_at__date=timezone.now().date()
        ).order_by('-published_at').first()
        
        if not latest_post:
            raise ValueError("No post was created despite successful command execution")
            
        logger.info(f"✅ Successfully generated post: {latest_post.title}")
        return {
            'status': 'success',
            'post_id': latest_post.id,
            'title': latest_post.title,
            'category': latest_post.category
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate blog post: {str(e)}")
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)
    
    finally:
        # Ensure we always update the scheduler status
        scheduler = PostScheduler.objects.get_or_create(pk=1)[0]
        scheduler.is_running = False
        scheduler.last_run = timezone.now()
        scheduler.save()
@shared_task
def generate_daily_post():
    """Scheduled task for daily post generation"""
    try:
        scheduler = PostScheduler.objects.get_or_create(pk=1)[0]
        if scheduler.last_run.date() < timezone.now().date() and not scheduler.is_running:
            generate_blog_post.delay()
    except Exception as e:
        logger.error(f"❌ Error in daily post scheduler: {str(e)}")
        raise