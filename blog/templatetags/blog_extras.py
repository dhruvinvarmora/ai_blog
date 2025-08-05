from django import template
import re

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