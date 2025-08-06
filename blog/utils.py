import os
import random
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.conf import settings
import mimetypes
import hashlib
from PIL import Image
import io
import numpy as np
def download_image(url, filename=None):
    """Download image from URL and return as ContentFile with unique filename"""
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Create unique filename
        parsed = urlparse(url)
        unique_id = hashlib.md5(url.encode()).hexdigest()[:12]
        
        # Get content type for extension
        content_type = response.headers.get('content-type', '')
        extension = mimetypes.guess_extension(content_type) or '.jpg'
        
        # Create filename with plant prefix
        filename = f"plant-{unique_id}{extension}"
        
        return ContentFile(response.content, name=filename), filename
            
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None, None

def is_plant_image(image_file):
    """More lenient plant image verification"""
    try:
        from PIL import Image
        import io
        import numpy as np
        
        # Open image
        img = Image.open(io.BytesIO(image_file.read()))
        
        # Convert to array
        img_array = np.array(img)
        
        # Check for dominant green colors (HSV space)
        hsv_img = img.convert('HSV')
        h,s,v = hsv_img.split()
        green_pixels = np.sum((np.array(h) > 30) & (np.array(h) < 90))
        total_pixels = img_array.shape[0] * img_array.shape[1]
        
        # Consider it a plant if >15% green or looks like a flower
        return (green_pixels/total_pixels > 0.15) or ('flower' in image_file.name.lower())
        
    except Exception:
        return True  # Fallback to accept image if verification fails

def optimize_image(image_file, max_size=(1200, 800), quality=85):
    """
    Optimize image for web display before uploading to Cloudinary
    """
    try:
        # Open image directly from ContentFile
        img = Image.open(io.BytesIO(image_file.read()))
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized image to bytes buffer
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return ContentFile(output.getvalue(), name=image_file.name)
        
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return image_file

def get_plant_specific_images(plant_name, category, count=6):
    """
    Get plant-specific image URLs based on category and plant name
    """
    base_queries = {
        'plants': [
            f"{plant_name} plant",
            f"{plant_name} indoor plant",
            f"{plant_name} care",
            f"{plant_name} close up",
            f"{plant_name} healthy",
            f"{plant_name} home decor"
        ],
        'flowers': [
            f"{plant_name} flower",
            f"{plant_name} bloom",
            f"{plant_name} garden",
            f"{plant_name} close up",
            f"{plant_name} bouquet",
            f"{plant_name} field"
        ],
        'fruits': [
            f"{plant_name} fruit",
            f"{plant_name} harvest",
            f"{plant_name} tree",
            f"{plant_name} ripe",
            f"{plant_name} orchard",
            f"{plant_name} fresh"
        ],
        'gardening': [
            f"{plant_name} gardening",
            f"{plant_name} soil",
            f"{plant_name} tools",
            f"{plant_name} garden bed",
            f"{plant_name} organic",
            f"{plant_name} sustainable"
        ],
        'care': [
            f"{plant_name} watering",
            f"{plant_name} pruning",
            f"{plant_name} fertilizing",
            f"{plant_name} repotting",
            f"{plant_name} maintenance",
            f"{plant_name} health"
        ]
    }
    
    queries = base_queries.get(category, base_queries['plants'])
    return queries[:count]

def create_image_captions(plant_name, context, section_title_or_image_type=None):
    """
    Create section-specific or type-specific captions for plant images
    """
    # Section-based captions
    section_captions = {
        'Light Requirements': [
            f"Ideal lighting setup for {plant_name}",
            f"{plant_name} in perfect sunlight conditions",
            f"Proper light exposure for healthy {plant_name}"
        ],
        'Care Difficulty': [
            f"Understanding {plant_name} care requirements",
            f"Skill level needed for {plant_name} maintenance",
            f"{plant_name} difficulty assessment"
        ],
        'Watering Needs': [
            f"Proper watering technique for {plant_name}",
            f"How to water {plant_name} correctly",
            f"Moisture needs of {plant_name} plants"
        ],
        'Soil and Potting': [
            f"Best soil mix for {plant_name}",
            f"Potting requirements for {plant_name}",
            f"Root system and soil needs for {plant_name}"
        ],
        'Temperature and Humidity': [
            f"Climate conditions for {plant_name}",
            f"Humidity preferences of {plant_name}",
            f"Temperature range for thriving {plant_name}"
        ],
        'Growth Rate and Maximum Height': [
            f"Growth timeline of {plant_name}",
            f"Mature size expectations for {plant_name}",
            f"Tracking {plant_name}'s development"
        ],
        'Troubleshooting Common Issues': [
            f"Solving {plant_name} plant problems",
            f"Common {plant_name} issues and solutions",
            f"Reviving struggling {plant_name}"
        ],
        'Fertilizing': [
            f"Feeding schedule for {plant_name}",
            f"Nutrient requirements of {plant_name}",
            f"Best fertilizers for {plant_name}"
        ],
        'Cleaning': [
            f"Proper {plant_name} leaf maintenance",
            f"Dusting and cleaning {plant_name} foliage",
            f"Leaf care for shiny {plant_name} leaves"
        ],
        'Benefits': [
            f"Health benefits of {plant_name}",
            f"Why {plant_name} makes a great houseplant",
            f"Advantages of growing {plant_name}"
        ]
    }
    
    # Check if we're handling a section title
    for section, captions in section_captions.items():
        if section.lower() in section_title_or_image_type.lower():
            return random.choice(captions)
    
    # Image type-based captions
    type_captions = {
        'overview': [
            f"Overview of {plant_name} plant",
            f"Full view of healthy {plant_name}",
            f"{plant_name} in natural environment"
        ],
        'care': [
            f"Caring for {plant_name} plant",
            f"Maintenance tips for {plant_name}",
            f"{plant_name} care techniques"
        ],
        'closeup': [
            f"Close-up of {plant_name} details",
            f"Detailed view of {plant_name}",
            f"Intricate details of {plant_name}"
        ],
        'indoor': [
            f"{plant_name} as indoor plant",
            f"Indoor {plant_name} decoration",
            f"Growing {plant_name} inside home"
        ],
        'healthy': [
            f"Healthy {plant_name} specimen",
            f"Thriving {plant_name} example",
            f"Vibrant {plant_name} in peak condition"
        ],
        'decor': [
            f"{plant_name} in home decor",
            f"Styling with {plant_name}",
            f"Decorative use of {plant_name}"
        ]
    }
    
    # Category-specific overrides
    if context == 'flowers':
        type_captions['overview'] = [
            f"Beautiful {plant_name} flowers",
            f"{plant_name} in full bloom",
            f"Colorful {plant_name} display"
        ]
    elif context == 'fruits':
        type_captions['overview'] = [
            f"Fresh {plant_name} fruits",
            f"Ripe {plant_name} ready for harvest",
            f"{plant_name} fruit on the tree"
        ]
    
    return random.choice(type_captions.get(section_title_or_image_type, [f"{plant_name} plant"]))

def generate_alt_text(plant_name, category, image_type):
    """
    Generate descriptive alt text for accessibility
    """
    alt_texts = {
        'plants': {
            'overview': f"{plant_name} plant in natural environment",
            'care': f"{plant_name} plant care and maintenance",
            'closeup': f"Close-up view of {plant_name} plant details",
            'indoor': f"{plant_name} plant as indoor decoration",
            'healthy': f"Healthy {plant_name} plant specimen",
            'decor': f"{plant_name} plant in home decor setting"
        },
        'flowers': {
            'overview': f"{plant_name} flowers in full bloom",
            'care': f"{plant_name} flower care guide",
            'closeup': f"Close-up of {plant_name} flower petals",
            'garden': f"{plant_name} flowers in garden setting",
            'bouquet': f"{plant_name} flower arrangement",
            'field': f"Field of {plant_name} flowers"
        },
        'fruits': {
            'overview': f"Ripe {plant_name} fruits on tree",
            'care': f"{plant_name} fruit growing guide",
            'closeup': f"Close-up of {plant_name} fruit details",
            'tree': f"{plant_name} tree with fruits",
            'ripe': f"Ripe {plant_name} fruits ready for harvest",
            'fresh': f"Fresh {plant_name} fruits"
        }
    }
    
    # For gardening and care, use the plants category as default
    if category in alt_texts:
        category_alts = alt_texts[category]
    else:
        category_alts = alt_texts['plants']
    
    return category_alts.get(image_type, f"{plant_name} plant image")