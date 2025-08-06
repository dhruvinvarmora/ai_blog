from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post, Tag, PostImage
from blog.utils import (
    download_image, is_plant_image, optimize_image, get_plant_specific_images,
    create_image_captions, generate_alt_text
)
import logging
from django.core.files.base import ContentFile
import re
import json
import random
import google.generativeai as genai
from decouple import config
import requests
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blog_generation.log'),
        logging.StreamHandler()
    ]
)

# Configure Cloudinary
cloudinary.config(
    cloud_name=config('CLOUDINARY_CLOUD_NAME'),
    api_key=config('CLOUDINARY_API_KEY'),
    api_secret=config('CLOUDINARY_API_SECRET'),
    secure=True
)

genai.configure(api_key=config("GEMINI_API_KEY"))

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

class Command(BaseCommand):
    help = "Generate automated daily blog posts about plants, flowers, and fruits with local image storage"

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            choices=['plants', 'flowers', 'fruits', 'gardening', 'care'],
            default=None,
            help='Specific category to generate post for'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if post exists'
        )
    
    def log_error(self, message, exc_info=False):
        """Helper method for consistent error logging"""
        logger.error(message, exc_info=exc_info)
        self.stdout.write(self.style.ERROR(message))

    def log_info(self, message):
        """Helper method for consistent info logging"""
        logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))

    def log_warning(self, message):
        """Helper method for consistent warning logging"""
        logger.warning(message)
        self.stdout.write(self.style.WARNING(message))

    def log_debug(self, message):
        """Helper method for debug logging"""
        if self.verbose:
            logger.debug(message)
            self.stdout.write(self.style.NOTICE(message))

    def get_unsplash_images(self, query, count=6):
        """Get multiple relevant plant images from Unsplash"""
        images = []
        try:
            access_key = config("UNSPLASH_ACCESS_KEY")
            if not access_key:
                self.log_error("❌ Unsplash access key not configured")
                return images
            
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            
            response = session.get(
                "https://api.unsplash.com/search/photos",
                params={
                    'query': f"{query} plant|foliage|leaf|flower|fruit|botanical",
                    'per_page': count,
                    'orientation': 'landscape',
                    'content_filter': 'high'
                },
                headers={'Authorization': f'Client-ID {access_key}'},
                timeout=15
            )
            response.raise_for_status()
            
            return [
                {
                    'url': photo['urls']['regular'],
                    'description': (photo.get('description') or photo.get('alt_description') or query),
                    'id': photo['id']
                }
                for photo in response.json().get('results', [])[:count]
            ]
            
        except Exception as e:
            self.log_error(f"❌ Error fetching images: {e}", exc_info=True)
            return images

    def upload_to_cloudinary(self, image_url, public_id):
        try:
            result = cloudinary.uploader.upload(
                image_url,
                public_id=public_id,
                folder="blog",
                use_filename=True,
                unique_filename=False,
                overwrite=True,
                resource_type="image",
                transformation={"fetch_format": "auto", "quality": "auto"},
            )
            return result["secure_url"]
        except Exception as e:
            self.log_error(f"Cloudinary upload failed: {e}", exc_info=True)
            return None

    def download_and_store_image(self, image_url, post, caption, alt_text, order, image_type):
        """
        Downloads an image from a URL and uploads it to Cloudinary, attaching it to the post.
        """
        try:
            # Create a public ID for Cloudinary
            public_id = f"{slugify(post.title)}-{image_type}-{order}"
            
            # Upload to Cloudinary
            cloudinary_url = self.upload_to_cloudinary(image_url, public_id)

            if not cloudinary_url:
                self.log_warning(f"⚠️ Cloudinary upload failed for {image_type}, using placeholder.")
                return None

            # Create and save PostImage
            post_image = PostImage(
                post=post,
                image=cloudinary_url,
                image_url=cloudinary_url,
                caption=caption,
                alt_text=alt_text,
                order=order,
                image_type=image_type
            )
            post_image.save()
            return post_image

        except Exception as e:
            self.log_error(f"[ERROR] Image processing failed: {e}", exc_info=True)
            return None

    def download_and_store_main_images(self, post, plant_name, category):
        """Download thumbnail and featured images with proper error handling"""
        try:
            # Initialize default placeholder URLs
            cloudinary_cloud_name = config("CLOUDINARY_CLOUD_NAME", default="demo")
            post.thumbnail_url = f"https://res.cloudinary.com/{cloudinary_cloud_name}/image/upload/v1/plant-placeholder.jpg"
            post.featured_image_url = f"https://res.cloudinary.com/{cloudinary_cloud_name}/image/upload/v1/plant-featured-placeholder.jpg"
            
            # Download thumbnail
            thumbnail_images = self.get_unsplash_images(f"{plant_name} {category}", 1)
            if thumbnail_images:
                thumbnail_image = self.download_and_store_image(
                    thumbnail_images[0]['url'],
                    post,
                    f"{plant_name} {category} thumbnail",
                    f"{plant_name} plant thumbnail",
                    0,  # special order for main images
                    "thumbnail"
                )
                if thumbnail_image:
                    post.thumbnail = thumbnail_image.image
                    post.thumbnail_url = thumbnail_images[0]['url']
                    self.log_info(f"📸 Downloaded thumbnail: {thumbnail_image.image.url}")

            # Download featured image
            featured_images = self.get_unsplash_images(f"{plant_name} close up", 1)
            if featured_images:
                featured_image = self.download_and_store_image(
                    featured_images[0]['url'],
                    post,
                    f"Close up of {plant_name}",
                    f"Close up photo of {plant_name} plant",
                    0,  # special order for main images
                    "featured"
                )
                if featured_image:
                    post.featured_image = featured_image.image
                    post.featured_image_url = featured_images[0]['url']
                    self.log_info(f"📸 Downloaded featured image: {featured_image.image.url}")

            post.save()
            return True
            
        except Exception as e:
            self.log_error(f"❌ Main image processing failed: {e}", exc_info=True)
            # Even if failed, proceed with placeholder images
            post.save()
            return False


    def get_youtube_video(self, query):
        """Get a relevant YouTube video URL"""
        try:
            # Using a simple search approach - in production you'd use YouTube API
            search_query = quote(f"{query} plant care guide")
            return f"https://www.youtube.com/results?search_query={search_query}"
        except:
            return ""

    def get_daily_topics(self):
        """Get daily rotating topics for plants, flowers, and fruits"""
        topics = {
            'plants': [
                "Monstera Deliciosa Care Guide",
                "Snake Plant Benefits and Care",
                "Pothos Plant Propagation",
                "ZZ Plant Care Tips",
                "Fiddle Leaf Fig Care",
                "Peace Lily Care Guide",
                "Aloe Vera Plant Benefits",
                "Spider Plant Care",
                "Philodendron Care Tips",
                "Calathea Plant Care",
                "Bamboo Plant Care",
                "Succulent Care Guide",
                "Cactus Care Tips",
                "Fern Plant Care",
                "Palm Tree Care"
            ],
            'flowers': [
                "Rose Care and Maintenance",
                "Orchid Care Guide",
                "Tulip Growing Tips",
                "Sunflower Care",
                "Lavender Plant Care",
                "Daisy Flower Care",
                "Peony Care Guide",
                "Hydrangea Care Tips",
                "Daffodil Growing Guide",
                "Iris Flower Care",
                "Carnation Care",
                "Chrysanthemum Care",
                "Azalea Care Guide",
                "Camellia Care Tips",
                "Gardenia Care"
            ],
            'fruits': [
                "Strawberry Growing Guide",
                "Tomato Plant Care",
                "Citrus Tree Care",
                "Apple Tree Maintenance",
                "Blueberry Bush Care",
                "Raspberry Plant Care",
                "Grape Vine Care",
                "Peach Tree Care",
                "Cherry Tree Care",
                "Plum Tree Care",
                "Pear Tree Care",
                "Fig Tree Care",
                "Pomegranate Tree Care",
                "Avocado Tree Care",
                "Mango Tree Care"
            ],
            'gardening': [
                "Organic Gardening Tips",
                "Container Gardening Guide",
                "Indoor Gardening Tips",
                "Garden Soil Preparation",
                "Fertilizer Guide",
                "Pest Control Methods",
                "Pruning Techniques",
                "Seed Starting Guide",
                "Garden Planning Tips",
                "Watering Techniques",
                "Composting Guide",
                "Garden Tools Guide",
                "Seasonal Gardening Tips",
                "Vertical Gardening",
                "Herb Garden Care"
            ],
            'care': [
                "Plant Watering Guide",
                "Light Requirements for Plants",
                "Temperature Control for Plants",
                "Humidity for Indoor Plants",
                "Potting Mix Guide",
                "Repotting Plants",
                "Plant Disease Prevention",
                "Fertilizing Schedule",
                "Pruning Houseplants",
                "Plant Propagation Methods",
                "Seasonal Plant Care",
                "Plant Pest Management",
                "Root Rot Prevention",
                "Leaf Care Tips",
                "Plant Nutrition Guide"
            ]
        }
        return topics

    def generate_post_content(self, topic, category):
        """Generate detailed blog post content using Gemini AI with image suggestions"""
        
        prompt = f"""
        Create a comprehensive blog post about "{topic}" in the {category} category. 

        Requirements:
        1. Write a detailed 800-1000 word article with engaging headings and structure
        2. Include practical care tips and instructions
        3. Add interesting facts and benefits
        4. Include care difficulty level, watering needs, sunlight requirements
        5. Add scientific name and family information if applicable
        6. Include growth rate, max height, blooming/harvest seasons
        7. Make it informative and engaging for plant enthusiasts
        8. Insert image placeholders at logical points using [IMAGE:type] tags. 
            Place them after these sections:
            [IMAGE:overview] - After introduction
            [IMAGE:care] - After Care Difficulty
            [IMAGE:closeup] - After Watering Needs
            [IMAGE:indoor] - After Temperature and Humidity
            [IMAGE:healthy] - After Growth Rate
            [IMAGE:decor] - After Benefits section
        Example structure:
        <h2>Introduction</h2>
        <p>...</p>
        [IMAGE:overview]

        <h2>Care Difficulty</h2>
        <p>...</p>
        Return the response in this exact JSON format:
        {{
        "title": "Complete title",
        "content": "Full article content with HTML formatting",
        "summary": "SEO summary under 160 characters",
        "scientific_name": "Scientific name if applicable",
        "family": "Plant family",
        "care_difficulty": "easy/medium/hard",
        "watering_needs": "Watering requirements",
        "sunlight_requirements": "Light requirements",
        "growth_rate": "Growth rate description",
        "max_height": "Maximum height",
        "blooming_season": "Blooming season (for flowers)",
        "harvest_time": "Harvest time (for fruits)",
        "tags": ["tag1", "tag2", "tag3"],
        "video_search_query": "YouTube search query for related video",
        "image_suggestions": [
            {{
            "query": "specific image search term",
            "caption": "Engaging caption for the image",
            "alt_text": "Descriptive alt text for accessibility",
            "type": "overview/care/closeup/indoor/healthy/decor"
            }}
        ]
        }}

        Make sure the content is detailed, informative, and engaging for plant lovers. Include specific image suggestions that would make the post visually appealing.
        """

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            # Clean and parse JSON response
            content = response.text
            # Remove markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1]
            
            data = json.loads(content.strip())
            return data
            
        except Exception as e:
            print(f"Error generating content: {e}")
            return None

    def create_or_get_tags(self, tag_names):
        """Create or get existing tags"""
        tags = []
        for tag_name in tag_names:
            try:
                tag, created = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': slugify(tag_name)}
                )
                tags.append(tag)
            except Exception as e:
                # If tag already exists with different slug, get it
                try:
                    tag = Tag.objects.get(name=tag_name)
                    tags.append(tag)
                except Tag.DoesNotExist:
                    # Create with unique slug
                    unique_slug = f"{slugify(tag_name)}-{len(Tag.objects.all())}"
                    tag = Tag.objects.create(name=tag_name, slug=unique_slug)
                    tags.append(tag)
        return tags

    def download_and_store_post_images(self, post, plant_name, category):
        """Download and store multiple images for the post"""
        images_created = []
        
        # Get plant-specific image queries
        image_types = ['overview', 'care', 'closeup', 'indoor', 'healthy', 'decor']
        
        for i, image_type in enumerate(image_types):
            # Create search query
            query = f"{plant_name} {image_type}"
            
            # Get image from Unsplash
            unsplash_images = self.get_unsplash_images(query, 1)
            if unsplash_images:
                image_data = unsplash_images[0]
                
                # Create engaging caption
                caption = create_image_captions(plant_name, category, image_type)
                alt_text = generate_alt_text(plant_name, category, image_type)
                
                # Download and store image
                post_image = self.download_and_store_image(
                    image_data['url'],
                    post,
                    caption,
                    alt_text,
                    i+1,         # order number
                    image_type    # image type
                )
                
                if post_image:
                    images_created.append(post_image)
                    print(f"📸 Created image {i+1}: {caption}")
        
        return images_created

    def download_and_store_main_images(self, post, plant_name, category):
        """Download thumbnail and featured images"""
        try:
            # Download thumbnail
            thumbnail_query = f"{plant_name} {category}"
            thumbnail_images = self.get_unsplash_images(thumbnail_query, 1)
            if thumbnail_images:
                content_file, filename = download_image(thumbnail_images[0]['url'])
                if content_file:
                    optimized_content = optimize_image(content_file)
                    # Save properly using ContentFile
                    post.thumbnail.save(filename, optimized_content, save=False)
                    post.thumbnail_url = thumbnail_images[0]['url']
                    print(f"📸 Downloaded thumbnail: {filename}")
            
            # Download featured image
            featured_query = f"{plant_name} close up"
            featured_images = self.get_unsplash_images(featured_query, 1)
            if featured_images:
                content_file, filename = download_image(featured_images[0]['url'])
                if content_file:
                    optimized_content = optimize_image(content_file)
                    # Save properly using ContentFile
                    post.featured_image.save(filename, optimized_content, save=False)
                    post.featured_image_url = featured_images[0]['url']
                    print(f"📸 Downloaded featured image: {filename}")
            
            post.save()
            
        except Exception as e:
            print(f"❌ Error downloading main images: {e}")

    def handle(self, *args, **kwargs):
        try:
            category = kwargs.get('category')
            force = kwargs.get('force')
            # Get daily topics
            topics = self.get_daily_topics()
            
            # If no specific category, rotate through categories
            if not category:
                categories = list(topics.keys())
                # Use current date to determine which category to use today
                today = timezone.now().date()
                category_index = (today.day - 1) % len(categories)
                category = categories[category_index]
            
            # Get topic for today
            topic_list = topics[category]
            today = timezone.now().date()
            topic_index = (today.day - 1) % len(topic_list)
            topic = topic_list[topic_index]
            
            # Check if post already exists
            slug = slugify(topic)
            if Post.objects.filter(slug=slug).exists() and not force:
                self.stdout.write(self.style.WARNING(f"⚠️ Post already exists: {topic}"))
                return
            
            self.stdout.write(f"🌱 Generating post for category: {category}")
            self.stdout.write(f"📝 Topic: {topic}")
            
            # Generate content
            data = self.generate_post_content(topic, category)
            if not data:
                self.stdout.write(self.style.ERROR("❌ Failed to generate content"))
                return
            
            # Extract plant name from topic
            plant_name = topic.split()[0]  # Get first word as plant name
            
            # Get video URL
            video_url = self.get_youtube_video(data.get('video_search_query', topic))
            
            # Create tags
            tags = self.create_or_get_tags(data.get('tags', []))
            
            # Create post
            post = Post(
                title=data['title'],
                slug=slug,
                content=data['content'],
                summary=data['summary'],
                category=category,
                scientific_name=data.get('scientific_name', ''),
                family=data.get('family', ''),
                care_difficulty=data.get('care_difficulty', ''),
                watering_needs=data.get('watering_needs', ''),
                sunlight_requirements=data.get('sunlight_requirements', ''),
                growth_rate=data.get('growth_rate', ''),
                max_height=data.get('max_height', ''),
                blooming_season=data.get('blooming_season', ''),
                harvest_time=data.get('harvest_time', ''),
                video_url=video_url,
                published_at=timezone.now()
            )
            post.save()
            
            try:
                if not self.download_and_store_main_images(post, plant_name, category):
                    self.log_warning("Proceeding with placeholder images")
                    
                # Add tags
                post.tags.set(tags)
                
                # Download additional images
                try:
                    self.download_and_store_post_images(post, plant_name, category)
                except Exception as e:
                    self.log_error(f"Additional images failed: {e}", exc_info=True)
                    # Don't delete post - continue with whatever images we have
                    
                self.stdout.write(self.style.SUCCESS(f"✅ Post created successfully: {data['title']}"))
                self.stdout.write(f"📸 Thumbnail: {post.thumbnail.url if post.thumbnail else 'Placeholder'}")
                self.stdout.write(f"🎥 Video: {video_url}")
                self.stdout.write(f"🏷️ Tags: {', '.join([tag.name for tag in tags])}")
                self.stdout.write(f"🖼️ Created {post.images.count()} additional images")
                
            except Exception as e:
                self.log_error(f"Image processing failed: {str(e)}", exc_info=True)
                # Delete post if image processing fails completely
                post.delete()
                raise
                
        except Exception as e:
            self.log_error(f"Post generation failed: {str(e)}", exc_info=True)
            if 'post' in locals() and post.pk:
                post.delete()
                self.log_info("Deleted incomplete post due to error")