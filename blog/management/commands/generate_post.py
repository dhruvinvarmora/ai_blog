from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post, Tag, PostImage
from blog.utils import (
    create_image_captions, generate_alt_text
)
import re
import json
import google.generativeai as genai
from decouple import config
import requests
from urllib.parse import quote
import logging
import cloudinary
import cloudinary.uploader
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import psutil
import tracemalloc
from datetime import timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blog_generation.log', encoding='utf-8'),
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
    help = "Generate automated daily blog posts about plants, flowers, and fruits with Cloudinary image storage"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verbose = False
        self.session = requests.Session()
        self.setup_retry_strategy()
        self.genai_model = "gemini-1.5-flash"
        self.max_retries = 3
        self.chunk_size = 500
        tracemalloc.start()  # Start memory tracking

    def setup_retry_strategy(self):
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def add_arguments(self, parser):
        parser.add_argument('--category', type=str, choices=['plants', 'flowers', 'fruits', 'gardening', 'care'])
        parser.add_argument('--force', action='store_true')
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--task-id', type=str, help='Celery task ID for tracking')

    def log_memory(self, stage):
        """Log memory usage at different stages"""
        process = psutil.Process()
        mem_info = process.memory_info()
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        logger.debug(f"🧠 {stage} Memory Usage:")
        logger.debug(f"  - RSS: {mem_info.rss / 1024 / 1024:.2f} MB")
        logger.debug(f"  - VMS: {mem_info.vms / 1024 / 1024:.2f} MB")
        
        if self.verbose:
            for stat in top_stats[:3]:
                logger.debug(f"  - {stat}")

    def log_error(self, message, exc_info=False):
        logger.error(message, exc_info=exc_info)
        self.stdout.write(self.style.ERROR(message))

    def log_info(self, message):
        logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))

    def log_warning(self, message):
        logger.warning(message)
        self.stdout.write(self.style.WARNING(message))

    def log_debug(self, message):
        logger.debug(message)
        if self.verbose:
            self.stdout.write(self.style.NOTICE(message))

    def get_unsplash_images(self, query, count=6):
        """Get multiple relevant plant images from Unsplash with strict filtering"""
        images = []
        try:
            access_key = config("UNSPLASH_ACCESS_KEY", default="")
            if not access_key:
                self.log_warning("❌ Unsplash access key not configured")
                return images
            
            plant_query = f"{query} plant|foliage|leaf|flower|fruit|botanical|garden|nature"
            
            url = "https://api.unsplash.com/search/photos"
            params = {
                'query': plant_query,
                'per_page': count + 5,
                'orientation': 'landscape',
                'content_filter': 'high'
            }
            headers = {'Authorization': f'Client-ID {access_key}'}
            
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            plant_images = []
            for photo in data.get('results', []):
                plant_keywords = {'plant', 'foliage', 'leaf', 'flower', 'fruit', 'tree', 
                                'botanical', 'garden', 'nature', 'green', 'organic', 'grow'}
                tags = [tag['title'].lower() for tag in photo.get('tags', [])]
                description = (photo.get('description') or photo.get('alt_description') or "").lower()

                has_plant_keyword = any(keyword in description for keyword in plant_keywords)
                has_plant_tag = any(keyword in tags for keyword in plant_keywords)
                if not (has_plant_keyword or has_plant_tag):
                    self.log_debug(f"⚠️ Skipping non-plant image: {photo['id']}")
                    continue
                    
                plant_images.append({
                    'url': photo['urls']['regular'],
                    'id': photo['id'],
                    'description': description or query
                })
            
            return [
                {
                    'url': img['url'],
                    'caption': f"{img['description']} - {query}",
                    'alt_text': f"Photo of {query} plant",
                }
                for img in plant_images[:count]
            ]
            
        except Exception as e:
            self.log_error(f"❌ Error fetching plant images: {e}", exc_info=True)
            return images

    def upload_to_cloudinary(self, image_url, public_id):
        """Upload image to Cloudinary with proper error handling"""
        try:
            if not image_url or not public_id:
                raise ValueError("Missing required parameters for Cloudinary upload")
                
            result = cloudinary.uploader.upload(
                image_url,
                public_id=public_id,
                folder="blog",
                use_filename=True,
                unique_filename=True,
                overwrite=True,
                resource_type="image",
                transformation=[{"quality": "auto", "fetch_format": "auto"}],
                timeout=30
            )
            
            if not result or 'secure_url' not in result:
                raise ValueError("Invalid response from Cloudinary")
                
            return result['secure_url']
            
        except cloudinary.exceptions.Error as e:
            self.log_error(f"❌ Cloudinary API error: {str(e)}")
            return None
        except Exception as e:
            self.log_error(f"❌ Unexpected upload error: {str(e)}")
            return None

    def store_image(self, post, image_url, caption, alt_text, order, image_type):
        """Store image reference in database with Cloudinary URL"""
        try:
            public_id = f"{slugify(post.title)}-{image_type}-{order}"
            
            cloudinary_url = self.upload_to_cloudinary(image_url, public_id)
            
            if not cloudinary_url:
                self.log_warning(f"⚠️ Using placeholder for {image_type} image")
                placeholder = "https://res.cloudinary.com/demo/image/upload/v1/plant-placeholder.jpg"
                cloudinary_url = placeholder
            
            post_image = PostImage(
                post=post,
                image_url=cloudinary_url,
                caption=caption,
                alt_text=alt_text,
                order=order,
                image_type=image_type
            )
            post_image.save()
            return post_image
            
        except Exception as e:
            self.log_error(f"❌ Error storing image: {e}", exc_info=True)
            return None

    def get_youtube_video(self, query):
        """Get a relevant YouTube video URL"""
        try:
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
        "video_search_query": "YouTube search query for related video"
        }}
        """

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            content = response.text
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1]
            
            data = json.loads(content.strip())
            return data
            
        except Exception as e:
            self.log_error(f"❌ Error generating content: {e}", exc_info=True)
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
                self.log_warning(f"⚠️ Error creating tag {tag_name}: {e}")
        return tags

    def generate_post_stages(self, kwargs):
        """Generate post in stages with memory management"""
        try:
            self.log_memory("Before category selection")
            category = kwargs.get('category')
            topics = self.get_daily_topics()
            
            if not category:
                categories = list(topics.keys())
                today = timezone.now().date()
                category_index = (today.day - 1) % len(categories)
                category = categories[category_index]
            
            self.log_memory("After category selection")
            
            topic_list = topics[category]
            today = timezone.now().date()
            topic_index = (today.day - 1) % len(topic_list)
            topic = topic_list[topic_index]
            slug = slugify(topic)
            
            if Post.objects.filter(slug=slug).exists() and not kwargs.get('force'):
                self.log_warning(f"⚠️ Post already exists: {topic}")
                return None
            
            self.log_info(f"🌱 Generating post for category: {category}")
            self.log_info(f"📝 Topic: {topic}")
            
            self.log_memory("Before content generation")
            data = self.generate_post_content(topic, category)
            if not data:
                raise ValueError("Failed to generate content")
            
            self.log_memory("After content generation")
            return {
                'topic': topic,
                'slug': slug,
                'category': category,
                'data': data,
                'plant_name': topic.split()[0]
            }
            
        except Exception as e:
            self.log_error(f"❌ Error in post generation stages: {e}", exc_info=True)
            return None

    def handle_images(self, post_data, *args, **kwargs):
        """Handle all image-related operations"""
        try:
            self.verbose = kwargs.get('verbose', False)
            self.log_memory("Before image processing")
            data = post_data['data']
            plant_name = post_data['plant_name']
            category = post_data['category']
            
            post = Post(
                title=data['title'],
                slug=post_data['slug'],
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
                video_url=self.get_youtube_video(data.get('video_search_query', post_data['topic'])),
                published_at=timezone.now()
            )
            post.save()
            
            tags = self.create_or_get_tags(data.get('tags', []))
            post.tags.set(tags)
            
            # Process thumbnail and featured image
            thumbnail_query = f"{plant_name} {category}"
            thumbnail_images = self.get_unsplash_images(thumbnail_query, 1)
            
            if thumbnail_images:
                post.thumbnail_url = self.upload_to_cloudinary(
                    thumbnail_images[0]['url'],
                    f"{slugify(post.title)}-thumbnail"
                )
            
            featured_query = f"{plant_name} close up"
            featured_images = self.get_unsplash_images(featured_query, 1)
            
            if featured_images:
                post.featured_image_url = self.upload_to_cloudinary(
                    featured_images[0]['url'],
                    f"{slugify(post.title)}-featured"
                )
            
            post.save()
            
            # Process content images
            image_types = ['overview', 'care', 'closeup', 'indoor', 'healthy', 'decor']
            
            for i, image_type in enumerate(image_types):
                query = f"{plant_name} {image_type}"
                unsplash_images = self.get_unsplash_images(query, 1)
                
                if unsplash_images:
                    image_data = unsplash_images[0]
                    caption = create_image_captions(plant_name, category, image_type)
                    alt_text = generate_alt_text(plant_name, category, image_type)
                    
                    self.store_image(
                        post,
                        image_data['url'],
                        caption,
                        alt_text,
                        i+1,
                        image_type
                    )
            
            self.log_memory("After image processing")
            return post
            
        except Exception as e:
            self.log_error(f"❌ Error handling images: {e}", exc_info=True)
            if 'post' in locals() and post.pk:
                post.delete()
            raise

    def handle(self, *args, **kwargs):
        try:
            self.verbose = kwargs['verbose']
            self.log_info("🚀 Starting post generation process")
            self.log_memory("Initial memory usage")
            
            # Generate in stages with checkpoints
            post_data = self.generate_post_stages(kwargs)
            
            if post_data:
                # Optimized image handling
                post = self.handle_images(post_data)
                
                self.log_info(f"✅ Successfully created post: {post.title}")
                self.log_memory("Final memory usage")
                
                return {
                    'status': 'success',
                    'post_id': post.id,
                    'title': post.title
                }
            
        except Exception as e:
            self.log_error(f"❌ Post generation failed: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            tracemalloc.stop()