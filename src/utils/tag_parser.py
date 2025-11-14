import re

def parse_tags(text):
    """Extract <tag>...</tag> sections into a dict."""
    tags = {}
    pattern = r"<(\w+)>(.*?)</\1>"
    for tag, content in re.findall(pattern, text, flags=re.S):
        tags[tag] = content.strip()
    return tags