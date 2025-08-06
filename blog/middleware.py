from django.utils import timezone
from .models import PostScheduler
from .management.commands.generate_post import Command
from django.shortcuts import render

class DailyPostScheduler:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Run once per day
        scheduler, _ = PostScheduler.objects.get_or_create(pk=1)
        
        if scheduler.last_run.date() < timezone.now().date() and not scheduler.is_running:
            print('scheduler.is_running: ', scheduler.is_running)
            print('timezone.now().date(): ', timezone.now().date())
            print('scheduler.last_run.date(): ', scheduler.last_run.date())
            scheduler.is_running = True
            scheduler.save()
            
            try:
                Command().handle()
            finally:
                scheduler.is_running = False
                scheduler.last_run = timezone.now()
                scheduler.save()
                
        return self.get_response(request)
    

class Custom404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404:
            return render(request, '404.html', status=404)
        return response