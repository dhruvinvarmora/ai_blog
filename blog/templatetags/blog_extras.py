from django import template
import re
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def split_sections(content):
    """
    Split content into sections based on h2 headings
    Returns list of dictionaries with 'title' and 'content'
    """
    sections = []
    parts = re.split(r'(<h2.*?>.*?</h2>)', content)
    
    for i in range(1, len(parts), 2):
        sections.append({
            'title': re.sub(r'<.*?>', '', parts[i]).strip(),
            'content': parts[i] + parts[i+1]
        })
    
    return sections

@register.filter
def get_image_for_section(images, section_title):
    """
    Find the most relevant image for a section
    """
    section_keywords = {
        'Light Requirements': ['light', 'sun', 'window'],
        'Watering Needs': ['water', 'watering', 'moisture'],
        'Soil and Potting': ['soil', 'pot', 'repot'],
        'Temperature and Humidity': ['humidity', 'temperature', 'climate'],
        'Growth Rate': ['growth', 'size', 'height'],
        'Troubleshooting': ['problem', 'issue', 'yellow', 'brown'],
        'Fertilizing': ['fertilizer', 'feed', 'nutrients'],
        'Cleaning': ['clean', 'dust', 'shine'],
        'Benefits': ['benefit', 'air', 'health']
    }
    
    keywords = next((v for k,v in section_keywords.items() 
                   if k.lower() in section_title.lower()), [])
    
    for image in images:
        if any(keyword in image.caption.lower() for keyword in keywords):
            return image
    return images.first()  # Fallback to first image if no match



@register.filter
def add_section_images(content, images):
    """
    Insert images after each section heading in the content
    """
    # Group images by their order (which should match sections)
    sorted_images = sorted(images, key=lambda x: x.order)
    
    # Split content by h2 headings
    parts = re.split(r'(<h2.*?>.*?</h2>)', content)
    result = []
    
    for i, part in enumerate(parts):
        result.append(part)
        # Insert image after every odd-indexed part (which are the h2 sections)
        if i % 2 == 1 and (i//2) < len(sorted_images):
            img = sorted_images[i//2]
            result.append(
                f'<div class="section-image mb-4">'
                f'<img src="{img.image.url}" class="img-fluid rounded" alt="{img.alt_text}">'
                f'<p class="image-caption text-muted mt-2">{img.caption}</p>'
                f'</div>'
            )
    
    return ''.join(result)    

@register.filter
def insert_images(content, post):
    """
    Replace [IMAGE:type] placeholders with actual images
    and add section-specific images
    """
    # First handle the explicit placeholders
    images_by_type = {img.image_type: img for img in post.images.all()}
    for image_type, image in images_by_type.items():
        placeholder = f'[IMAGE:{image_type}]'
        if placeholder in content:
            img_html = f"""
            <div class="post-image mb-4 text-center">
                <img src="{image.image.url}" 
                     class="img-fluid rounded shadow" 
                     alt="{image.alt_text}"
                     style="max-height: 500px;">
                <div class="image-caption mt-2 fst-italic">
                    {image.caption}
                </div>
            </div>
            """
            content = content.replace(placeholder, img_html)
    
    # Then add images between sections
    sections = split_into_sections(content)
    if sections and post.images.count() > 0:
        content = insert_section_images(sections, post.images.all())
    
    return mark_safe(content)

def split_into_sections(content):
    """Split content by h2 headings"""
    return re.split(r'(<h2.*?>.*?</h2>)', content)

def insert_section_images(sections, images):
    """Insert images between sections"""
    result = []
    sorted_images = sorted(images, key=lambda x: x.order)
    
    for i, section in enumerate(sections):
        result.append(section)
        # Insert image after every heading (odd indices)
        if i % 2 == 1 and (i//2) < len(sorted_images):
            img = sorted_images[i//2]
            result.append(
                f'<div class="section-image mb-4">'
                f'<img src="{img.image.url}" class="img-fluid rounded" alt="{img.alt_text}">'
                f'<p class="image-caption text-muted mt-2">{img.caption}</p>'
                f'</div>'
            )
    
    return ''.join(result)