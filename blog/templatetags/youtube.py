from django import template
import re

register = template.Library()

@register.filter
def youtube_embed(url):
    # Converts YouTube watch URL to embed
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/embed/{video_id}"
    return url
