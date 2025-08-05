from django.utils import timezone
from .models import PostScheduler
from .management.commands.generate_post import Command

class DailyPostScheduler:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Run once per day
        scheduler, _ = PostScheduler.objects.get_or_create(pk=1)
        
        if scheduler.last_run.date() < timezone.now().date() and not scheduler.is_running:
            scheduler.is_running = True
            scheduler.save()
            
            try:
                Command().handle()
            finally:
                scheduler.is_running = False
                scheduler.last_run = timezone.now()
                scheduler.save()
                
        return self.get_response(request)