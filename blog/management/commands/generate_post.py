from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import Post, Tag, PostImage
from blog.utils import (
    download_image, is_plant_image, optimize_image, get_plant_specific_images,
    create_image_captions, generate_alt_text
)
import datetime
import os
import re
import json
import random
import google.generativeai as genai
from decouple import config
import requests
from urllib.parse import quote

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

    def get_unsplash_images(self, query, count=6):
        """Get multiple relevant plant images from Unsplash with strict filtering"""
        images = []
        try:
            access_key = config("UNSPLASH_ACCESS_KEY", default="")
            if not access_key:
                print("❌ Unsplash access key not configured")
                return images
            
            # Add plant-specific filters to the query
            plant_query = f"{query} plant|foliage|leaf|flower|fruit|botanical|garden|nature"
            
            url = "https://api.unsplash.com/search/photos"
            params = {
                'query': plant_query,
                'per_page': count + 5,  # Get extras to filter out non-plant images
                'orientation': 'landscape',
                'content_filter': 'high'  # Higher quality content
            }
            headers = {'Authorization': f'Client-ID {access_key}'}
            
            response = requests.get(url, params=params, headers=headers)
            if response.status_code != 200:
                print(f"❌ Unsplash API error: {response.status_code} - {response.text}")
                return images
            
            data = response.json()
            plant_images = []
            
            for photo in data.get('results', []):
                # Skip if not plant-related based on tags or description
                tags = [tag['title'].lower() for tag in photo.get('tags', [])]
                description = (photo.get('description') or photo.get('alt_description') or "").lower()
                
                # Check for plant-related keywords
                plant_keywords = {'plant', 'foliage', 'leaf', 'flower', 'fruit', 'tree', 
                                'botanical', 'garden', 'nature', 'green', 'organic', 'grow'}
                
                has_plant_keyword = any(keyword in description for keyword in plant_keywords)
                has_plant_tag = any(keyword in tags for keyword in plant_keywords)
                
                if not (has_plant_keyword or has_plant_tag):
                    print(f"⚠️ Skipping non-plant image: {photo['id']}")
                    continue
                    
                plant_images.append({
                    'url': photo['urls']['regular'],
                    'id': photo['id'],
                    'description': description or query
                })
            
            # Return only the requested count of verified plant images
            return [
                {
                    'url': img['url'],
                    'caption': f"{img['description']} - {query}",
                    'alt_text': f"Photo of {query} plant",
                    'order': i+1
                }
                for i, img in enumerate(plant_images[:count])
            ]
            
        except Exception as e:
            print(f"❌ Error fetching plant images: {e}")
            return images


    def download_and_store_image(self, image_url, post, caption, alt_text, order):
        """Download image from URL and store locally using ContentFile"""
        try:
            # Download image - returns ContentFile and filename
            content_file, filename = download_image(image_url)
            if not content_file:
                print(f"❌ Failed to download image: {image_url}")
                return None
            
            if not is_plant_image(content_file.read()):
                print(f"⚠️ Skipping non-plant image: {image_url}")
                return None
            # Optimize image - returns optimized ContentFile
            optimized_content = optimize_image(content_file)
            
            # Create PostImage object
            post_image = PostImage(
                post=post,
                image_url=image_url,
                caption=caption,
                alt_text=alt_text,
                order=order
            )
            
            # Save the image file to the model
            post_image.image.save(
                filename,  # Use the generated filename
                optimized_content,  # The optimized ContentFile
                save=True  # Save the model instance
            )
            
            print(f"✅ Downloaded and stored: {filename}")
            return post_image
            
        except Exception as e:
            print(f"❌ Error storing image: {e}")
            return None

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
        8. Suggest 6 different types of images that would make the post visually appealing

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
                    i+1
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
                content, filename = download_image(thumbnail_images[0]['url'])
                if content:
                    optimized_content = optimize_image(content)
                    post.thumbnail = optimized_content
                    post.thumbnail_url = thumbnail_images[0]['url']
                    print(f"📸 Downloaded thumbnail: {filename}")
            
            # Download featured image
            featured_query = f"{plant_name} close up"
            featured_images = self.get_unsplash_images(featured_query, 1)
            if featured_images:
                content, filename = download_image(featured_images[0]['url'])
                if content:
                    optimized_content = optimize_image(content)
                    post.featured_image = optimized_content
                    post.featured_image_url = featured_images[0]['url']
                    print(f"📸 Downloaded featured image: {filename}")
            
            post.save()
            
        except Exception as e:
            print(f"❌ Error downloading main images: {e}")

    def handle(self, *args, **kwargs):
        success = False
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
                print(f"⚠️ Post already exists: {topic}")
                return
            
            print(f"🌱 Generating post for category: {category}")
            print(f"📝 Topic: {topic}")
            
            # Generate content
            data = self.generate_post_content(topic, category)
            if not data:
                print("❌ Failed to generate content")
                return
            
            # Extract plant name from topic
            plant_name = topic.split()[0]  # Get first word as plant name
            
            # Get video URL
            video_url = self.get_youtube_video(data.get('video_search_query', topic))
            
            # Create tags
            tags = self.create_or_get_tags(data.get('tags', []))
            
            # Create post
            post = Post.objects.create(
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
            
            # Add tags
            post.tags.set(tags)
            
            # Download and store main images (thumbnail and featured)
            self.download_and_store_main_images(post, plant_name, category)
            
            # Download and store additional images
            self.download_and_store_post_images(post, plant_name, category)

            if post.thumbnail or post.featured_image:
                success = True
            
            print(f"✅ Post created successfully: {data['title']}")
            print(f"📸 Thumbnail: {post.thumbnail_display}")
            print(f"🎥 Video: {video_url}")
            print(f"🏷️ Tags: {', '.join([tag.name for tag in tags])}")
            print(f"🖼️ Created {post.images.count()} additional images")
            print(f"💾 All images stored locally in media/posts/{post.slug}/")
        except Exception as e:
            print(f"❌ Error in post generation: {e}")
            # Delete the post if it was partially created
            if 'post' in locals() and post.pk:
                post.delete()
                print("❌ Deleted incomplete post due to error")
    
        return success
