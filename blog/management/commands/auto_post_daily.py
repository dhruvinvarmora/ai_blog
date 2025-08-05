from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Automatically generate daily blog posts about plants, flowers, and fruits"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually creating posts'
        )

    def handle(self, *args, **kwargs):
        dry_run = kwargs.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN MODE - No posts will be created"
                )
            )
        
        try:
            # Generate today's post
            self.stdout.write(
                self.style.SUCCESS(
                    f"🌱 Starting daily post generation for {timezone.now().strftime('%Y-%m-%d')}"
                )
            )
            
            if not dry_run:
                call_command('generate_post')
                self.stdout.write(
                    self.style.SUCCESS(
                        "✅ Daily post generated successfully!"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✅ Dry run completed - post would be generated"
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error generating daily post: {str(e)}"
                )
            )
            logger.error(f"Daily post generation failed: {str(e)}") 