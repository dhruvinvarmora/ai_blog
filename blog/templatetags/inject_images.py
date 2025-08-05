import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def inject_images(content, images):
    headings = [
        "Light Requirements",
        "Care Difficulty",
        "Watering Needs",
        "Soil and Potting",
        "Temperature and Humidity",
        "Growth Rate and Maximum Height",
        "Blooming and Harvest",
        "Troubleshooting Common Issues",
        "Fertilizing",
        "Cleaning",
        "Benefits",
        "Conclusion",
    ]
    imgs = list(images)

    def replacer(match):
        section = match.group(1)
        html = match.group(0)
        if section in headings and imgs:
            img = imgs.pop(0)
            img_html = (
                f'<div class="injected-image">'
                f'  <img src="{ img.image.url }" alt="{ img.alt_text }" class="img-fluid rounded mb-3"/>'
                f'  <div class="image-caption">{ img.caption }</div>'
                f'</div>'
            )
            return html + img_html
        return html

    pattern = re.compile(r'<h2[^>]*>(.*?)</h2>', flags=re.IGNORECASE)
    new_content = pattern.sub(replacer, content)
    return mark_safe(new_content)
