import re
import markdown


def md_to_html(content, extensions=None):
    if extensions is None:
        extensions = ["extra", "tables", "fenced_code", "codehilite", "toc", "sane_lists"]
    return markdown.markdown(content, extensions=extensions, output_format="html5")


def extract_title(content, config):
    if config.first_h1_as_title:
        match = re.search(r"^#\s+(.+?)(?:\s*#+\s*)?$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def remove_first_h1(content):
    return re.sub(r"^#\s+.*?(\n|$)", "", content, count=1)
