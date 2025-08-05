import os
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.conf import settings
import mimetypes
import hashlib
from PIL import Image
import io

def download_image(url, filename=None):
    """Download image from URL and return as ContentFile with unique filename"""
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        # Create unique filename using Unsplash ID
        parsed = urlparse(url)
        path = parsed.path
        unique_id = path.split('/')[-1] if path else hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Get content type for extension
        content_type = response.headers.get('content-type', '')
        extension = mimetypes.guess_extension(content_type) or '.jpg'
        
        # Create filename with plant prefix
        filename = f"plant-{unique_id}{extension}"
        
        return ContentFile(response.content, name=filename), filename
            
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None, None

def is_plant_image(image_content):
    """Simple verification that image contains plants"""
    try:
        from PIL import Image
        import io
        import numpy as np
        
        # Open image and convert to RGB
        img = Image.open(io.BytesIO(image_content)).convert('RGB')
        img = img.resize((224, 224))  # Resize for processing
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Calculate green pixel percentage
        green_pixels = np.sum(
            (img_array[:, :, 1] > img_array[:, :, 0]) & 
            (img_array[:, :, 1] > img_array[:, :, 2])
        )
        green_percentage = green_pixels / (224 * 224)
        
        # Consider it a plant image if >15% green
        return green_percentage > 0.15
        
    except Exception as e:
        print(f"⚠️ Plant verification failed: {e}")
        return True  # Assume valid if verification fails

def optimize_image(image_file, max_size=(1200, 800), quality=85):
    """
    Optimize image for web display
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
        
        # Create new ContentFile with original filename
        return ContentFile(output.getvalue(), name=image_file.name)
        
    except Exception as e:
        print(f"Error optimizing image: {e}")
        # Return original content if optimization fails
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

def create_image_captions(plant_name, category, image_type):
    """
    Create engaging captions for plant images
    """
    captions = {
        'plants': {
            'overview': f"Beautiful {plant_name} plant in its natural habitat",
            'care': f"Essential care tips for your {plant_name} plant",
            'closeup': f"Detailed view of {plant_name} leaves and structure",
            'indoor': f"{plant_name} as a stunning indoor decoration",
            'healthy': f"Healthy and thriving {plant_name} specimen",
            'decor': f"{plant_name} adding elegance to your home"
        },
        'flowers': {
            'overview': f"Stunning {plant_name} flowers in full bloom",
            'care': f"Expert care guide for {plant_name} flowers",
            'closeup': f"Close-up of beautiful {plant_name} petals",
            'garden': f"{plant_name} flowers in a vibrant garden",
            'bouquet': f"Gorgeous {plant_name} flower arrangement",
            'field': f"Breathtaking field of {plant_name} flowers"
        },
        'fruits': {
            'overview': f"Ripe and juicy {plant_name} fruits",
            'care': f"Growing and harvesting {plant_name} fruits",
            'closeup': f"Detailed view of {plant_name} fruit structure",
            'tree': f"{plant_name} tree laden with fruits",
            'ripe': f"Perfectly ripe {plant_name} ready for harvest",
            'fresh': f"Fresh and organic {plant_name} fruits"
        },
        'gardening': {
            'overview': f"Professional {plant_name} gardening techniques",
            'care': f"Essential gardening tips for {plant_name}",
            'closeup': f"Detailed gardening process for {plant_name}",
            'soil': f"Perfect soil preparation for {plant_name}",
            'organic': f"Organic gardening methods for {plant_name}",
            'sustainable': f"Sustainable {plant_name} gardening practices"
        },
        'care': {
            'overview': f"Complete care guide for {plant_name}",
            'watering': f"Proper watering techniques for {plant_name}",
            'pruning': f"Expert pruning tips for {plant_name}",
            'fertilizing': f"Fertilizing schedule for {plant_name}",
            'maintenance': f"Regular maintenance for {plant_name}",
            'health': f"Keeping your {plant_name} healthy and strong"
        }
    }
    
    category_captions = captions.get(category, captions['plants'])
    return category_captions.get(image_type, f"Beautiful {plant_name}")

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
    
    category_alts = alt_texts.get(category, alt_texts['plants'])
    return category_alts.get(image_type, f"{plant_name} plant image") 