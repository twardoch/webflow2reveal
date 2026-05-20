# this_file: py/src/webflow2reveal/compiler.py

import os
import re
import sys
import http.server
import socketserver
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

def parse_css_background_colors(css_content: str) -> dict:
    """
    Parses CSS rules from text and maps class selectors to background-colors.
    """
    # Remove comments
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    # Match standard selector { rules } blocks
    block_pattern = re.compile(r'([^{]+)\{([^}]+)\}', re.DOTALL)
    bg_color_pattern = re.compile(r'background-color:\s*([^;!]+)', re.IGNORECASE)
    bg_pattern = re.compile(r'\bbackground:\s*([^;!]+)', re.IGNORECASE)
    
    class_colors = {}
    
    for selector, rules in block_pattern.findall(css_content):
        bg_color_match = bg_color_pattern.search(rules)
        bg_match = bg_pattern.search(rules)
        
        color = None
        if bg_color_match:
            color = bg_color_match.group(1).strip()
        elif bg_match:
            val = bg_match.group(1).strip()
            # Simple check if the background property acts like a solid color
            if val.startswith('#') or val in ('red', 'blue', 'green', 'white', 'black', 'transparent') or val.startswith('rgb'):
                color = val
                
        if color:
            for part in selector.split(','):
                part = part.strip()
                # Find class names like .kapr-brief
                for cls in re.findall(r'\.([a-zA-Z0-9_-]+)', part):
                    class_colors[cls] = color
                    
    return class_colors

def is_slide_section(section) -> bool:
    """
    Determines if a section tag is likely to be a slide, filtering out navbar and footer.
    """
    classes = section.get('class', [])
    classes_str = ' '.join(classes).lower()
    
    # Filter out known header/footer/menu sections
    if any(k in classes_str for k in ('menu', 'nav', 'footer', 'header', 'banner')):
        return False
    if section.get('id') in ('top', 'summary'):
        return False
    if section.find('vexy-menu') or section.find('vexy-footer'):
        return False
        
    return True

def get_section_bg_color(classes: list, class_colors: dict) -> str:
    """
    Resolves the background color for a list of classes, picking the most specific non-transparent color.
    """
    for cls in reversed(classes):
        color = class_colors.get(cls)
        if color and color not in ('transparent', '#0000', 'rgba(0,0,0,0)', 'rgba(0, 0, 0, 0)'):
            return color
    return None

def add_class(tag, class_name):
    classes = tag.get("class", [])
    if class_name not in classes:
        classes.append(class_name)
        tag["class"] = classes

def wrap_contents_in_div(soup, parent_tag, wrapper_class):
    wrapper = soup.new_tag("div", attrs={"class": wrapper_class})
    children = list(parent_tag.contents)
    to_wrap = []
    to_keep = []
    
    for child in children:
        if child.name in ('script', 'style'):
            to_keep.append(child)
        elif child.name == 'div' and any(k in ' '.join(child.get('class', [])).lower() for k in ('mask', 'video-wrap', 'hover-video')):
            to_keep.append(child)
        else:
            to_wrap.append(child)
            
    for child in to_wrap:
        wrapper.append(child.extract())
        
    parent_tag.append(wrapper)
    for child in to_keep:
        parent_tag.append(child.extract())

def normalize_reveal_dom(soup, class_colors):
    sections = [sec for sec in soup.find_all("section") if is_slide_section(sec)]
    
    for sec in sections:
        add_class(sec, "slide-section")
        
        # 1. Background color extraction for this section
        sec_bg = get_section_bg_color(sec.get("class", []), class_colors)
        if sec_bg and not sec.get("data-background-color"):
            sec["data-background-color"] = sec_bg

        # Check if the section contains a card overlay (badge)
        badge_el = None
        for div in sec.find_all("div"):
            div_classes = ' '.join(div.get('class', [])).lower()
            if 'card' in div_classes or 'badge' in div_classes:
                badge_el = div
                break
                
        if badge_el:
            add_class(badge_el, "slide-badge")
            # If there's an image, mark it cover
            for img in sec.find_all("img"):
                add_class(img, "slide-image-cover")
                if img.parent:
                    add_class(img.parent, "slide-image-container")
            continue

        # Look for layout children
        direct_children = []
        for child in sec.find_all(recursive=False):
            if child.name in ('div', 'section'):
                classes_str = ' '.join(child.get('class', [])).lower()
                if not any(k in classes_str for k in ('menu', 'nav', 'footer', 'mask', 'header', 'banner')):
                    direct_children.append(child)
                    
        # Check if single direct child is a grid/container wrapper
        grid_wrapper = None
        layout_elements = direct_children
        if len(direct_children) == 1:
            wrapper = direct_children[0]
            wrapper_classes = ' '.join(wrapper.get('class', [])).lower()
            if any(k in wrapper_classes for k in ('grid', 'container', 'row', 'wrap', 'bleed')):
                wrapper_children = []
                for sub in wrapper.find_all(recursive=False):
                    if sub.name in ('div', 'section'):
                        sub_classes = ' '.join(sub.get('class', [])).lower()
                        if not any(k in sub_classes for k in ('mask', 'video-wrap', 'hover-video')):
                            wrapper_children.append(sub)
                if len(wrapper_children) > 0:
                    grid_wrapper = wrapper
                    layout_elements = wrapper_children

        # Split layout check
        if len(layout_elements) == 2:
            parent_container = grid_wrapper if grid_wrapper else sec
            add_class(parent_container, "slide-split-layout")
            
            for col in layout_elements:
                add_class(col, "slide-column")
                
                # Propagate background color if any
                col_bg = get_section_bg_color(col.get("class", []), class_colors)
                if col_bg:
                    col['style'] = col.get('style', '') + f"; background-color: {col_bg} !important;"
                    
                # Identify if it contains an image
                img_el = col.find("img")
                if img_el:
                    add_class(col, "slide-image-container")
                    add_class(img_el, "slide-image-cover")
                else:
                    # Text column. Wrap content
                    text_wrapper = None
                    children = [c for c in col.find_all(recursive=False) if c.name == 'div']
                    if len(children) == 1 and any('text' in cls.lower() or 'head' in cls.lower() for cls in children[0].get('class', [])):
                        text_wrapper = children[0]
                        
                    if text_wrapper:
                        add_class(text_wrapper, "slide-text-container")
                    else:
                        wrap_contents_in_div(soup, col, "slide-text-container")
            continue

        # Single cell / text layouts
        img_el = sec.find("img")
        has_text = len(sec.find_all(['h1', 'h2', 'h3', 'p'])) > 0
        if img_el and not has_text:
            parent = img_el.parent
            if parent:
                add_class(parent, "slide-image-container")
            add_class(img_el, "slide-image-cover")
        else:
            text_wrapper = None
            for div in sec.find_all("div"):
                div_classes = ' '.join(div.get('class', [])).lower()
                if any(k in div_classes for k in ('hero-wrap', 'container', 'front')):
                    text_wrapper = div
                    break
            if text_wrapper:
                add_class(text_wrapper, "slide-text-container")
            else:
                wrap_contents_in_div(soup, sec, "slide-text-container")

def convert(source: str, output: str = "index.html", serve: bool = False, port: int = 8000):
    """
    Converts a Webflow page to a Reveal.js presentation.
    
    Args:
        source: The URL (http/https) or local file path of the Webflow page.
        output: The output file path for the generated slide deck.
        serve: Whether to start a local development server after conversion.
        port: The port for the development server (default 8000).
    """
    print(f"Reading source from: {source}")
    if source.startswith("http://") or source.startswith("https://"):
        try:
            resp = requests.get(source, timeout=10)
            resp.raise_for_status()
            html_content = resp.text
        except Exception as e:
            print(f"Error fetching source URL: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if not os.path.exists(source):
            print(f"Error: Local file {source} does not exist.", file=sys.stderr)
            sys.exit(1)
        with open(source, "r", encoding="utf-8") as f:
            html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")
    class_colors = {}
    
    # 1. Parse inline style tags
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            class_colors.update(parse_css_background_colors(style_tag.string))
            
    # 2. Parse external linked stylesheets
    for link_tag in soup.find_all("link", rel="stylesheet"):
        href = link_tag.get("href")
        if not href:
            continue
        
        # Resolve stylesheet path
        if href.startswith("//"):
            css_url = "https:" + href
        elif not href.startswith("http") and source.startswith("http"):
            css_url = urljoin(source, href)
        elif not href.startswith("http") and not source.startswith("http"):
            # Local file resolution relative to source file directory
            src_dir = os.path.dirname(source)
            css_url = os.path.join(src_dir, href)
        else:
            css_url = href

        # Fetch/read CSS content
        try:
            if css_url.startswith("http://") or css_url.startswith("https://"):
                print(f"Fetching stylesheet: {css_url}")
                css_resp = requests.get(css_url, timeout=5)
                if css_resp.status_code == 200:
                    class_colors.update(parse_css_background_colors(css_resp.text))
            else:
                if os.path.exists(css_url):
                    print(f"Reading stylesheet: {css_url}")
                    with open(css_url, "r", encoding="utf-8") as f:
                        class_colors.update(parse_css_background_colors(f.read()))
        except Exception as e:
            print(f"Warning: could not resolve stylesheet {css_url}: {e}")

    # 3. Locate or wrap slide sections
    reveal_div = soup.select_one("div.reveal")
    slides_div = soup.select_one("div.reveal > div.slides")
    
    if reveal_div and slides_div:
        print("Found existing Reveal.js scaffold (div.reveal > div.slides).")
        sections = slides_div.find_all("section", recursive=False)
    else:
        print("Reveal.js scaffold not found or incomplete. Re-wrapping section elements...")
        # Find all loose sections
        all_sections = soup.find_all("section")
        sections = [sec for sec in all_sections if is_slide_section(sec)]
        
        # Extract them from their original positions and prepare to wrap them
        for sec in sections:
            sec.extract()
            
        # Create scaffold
        reveal_div = soup.new_tag("div", attrs={"class": "reveal"})
        slides_div = soup.new_tag("div", attrs={"class": "slides"})
        reveal_div.append(slides_div)
        
        for sec in sections:
            slides_div.append(sec)
            
        # Place the scaffold in the body
        if soup.body:
            soup.body.append(reveal_div)
        else:
            body = soup.new_tag("body")
            body.append(reveal_div)
            soup.append(body)

    # Normalize DOM structure dynamically for universal presentation styling
    normalize_reveal_dom(soup, class_colors)
    # Refresh sections list from the normalized DOM
    sections = slides_div.find_all("section", recursive=False)

    # 4. Set background colors using data-background-color attribute
    for sec in sections:
        classes = sec.get("class", [])
        bg_color = get_section_bg_color(classes, class_colors)
        if bg_color and not sec.get("data-background-color"):
            sec["data-background-color"] = bg_color
            print(f"Assigned background color {bg_color} to section {sec.get('id', '')}")

    # Determine background brightness and add slide-light-bg/slide-dark-bg classes
    for sec in sections:
        bg_color = sec.get("data-background-color")
        if bg_color:
            bg_color = bg_color.strip().lower()
            is_light = False
            if bg_color.startswith("#"):
                hex_color = bg_color[1:]
                try:
                    if len(hex_color) == 3:
                        r = int(hex_color[0] * 2, 16)
                        g = int(hex_color[1] * 2, 16)
                        b = int(hex_color[2] * 2, 16)
                    elif len(hex_color) == 6:
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                    else:
                        r, g, b = 255, 255, 255
                    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
                    if luminance > 0.6:
                        is_light = True
                except ValueError:
                    pass
            elif bg_color.startswith("rgb"):
                try:
                    import re
                    parts = re.findall(r"\d+", bg_color)
                    if len(parts) >= 3:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
                        if luminance > 0.6:
                            is_light = True
                except Exception:
                    pass
            elif bg_color in ("white", "yellow", "cyan", "lime"):
                is_light = True
            
            if is_light:
                add_class(sec, "slide-light-bg")
            else:
                add_class(sec, "slide-dark-bg")

    # 5. Inject Reveal.js styles and scripts
    if not soup.head:
        head = soup.new_tag("head")
        soup.insert(0, head)
        
    reveal_css = soup.new_tag("link", rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css")
    soup.head.append(reveal_css)

    # Custom styling overrides to scale layouts, prevent scrolling, and center sections
    custom_style = soup.new_tag("style")
    custom_style.string = """
    /* Prevent window/body scroll breakout */
    html, body {
      overflow: hidden !important;
      height: 100% !important;
      width: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
    }

    /* Presentation window baseline styles */
    .reveal {
      background-color: #0d0a06;
      color: #fff;
    }

    /* Zero slide margins (Rule 3) */
    .reveal .slides section.slide-section {
      height: 100% !important;
      box-sizing: border-box !important;
      overflow: hidden !important;
      position: relative !important;
      padding: 0 !important;
    }

    /* Universal split layouts */
    .reveal .slide-split-layout {
      display: grid !important;
      grid-template-columns: 1fr 1fr !important;
      grid-template-rows: 100% !important;
      width: 100% !important;
      height: 100% !important;
      max-width: 100% !important;
      max-height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      align-items: stretch !important;
      justify-items: stretch !important;
    }

    .reveal .slide-column {
      min-width: 0 !important;
      min-height: 0 !important;
      width: 100% !important;
      max-width: 100% !important;
      height: 100% !important;
      position: relative !important;
      margin: 0 !important;
      padding: 0 !important;
      box-sizing: border-box !important;
    }

    /* Override viewport-relative min-width from Webflow that crams right columns */
    .reveal .kapr-prov-left,
    .reveal .kapr-comp-a-left,
    .reveal .kapr-v1-right,
    .reveal .kapr-v2-left,
    .reveal .kapr-v3-right {
      min-width: 0 !important;
      width: 50% !important;
    }

    /* Image containment rules (Rule 4) */
    .reveal .slide-image-container {
      width: 100% !important;
      height: 100% !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      margin: 0 !important;
      padding: 0 !important;
      overflow: hidden !important;
      box-sizing: border-box !important;
    }

    /* Stretched full-bleed images by default */
    .reveal .slide-image-container img,
    .reveal .slide-image-cover,
    .reveal img.slide-image-cover {
      width: 100% !important;
      height: 100% !important;
      max-width: 100% !important;
      max-height: 100% !important;
      object-fit: cover !important;
    }

    /* Restoration assets in Slide 5 should fit completely without cropping */
    .reveal .kapr-img-restoration img {
      object-fit: contain !important;
    }

    /* 3/5 vertical centering from bottom (= 40% from top) (Rule 1 & 5) */
    .reveal section.slide-section:has(> .slide-text-container),
    .reveal .slide-column:has(> .slide-text-container) {
      display: flex !important;
      flex-direction: column !important;
      box-sizing: border-box !important;
      padding-top: 40px !important;
      padding-bottom: 40px !important;
    }

    .reveal section.slide-section:has(> .slide-text-container)::before,
    .reveal .slide-column:has(> .slide-text-container)::before {
      content: "" !important;
      display: block !important;
      flex: 4 1 0% !important;
    }

    .reveal section.slide-section:has(> .slide-text-container)::after,
    .reveal .slide-column:has(> .slide-text-container)::after {
      content: "" !important;
      display: block !important;
      flex: 6 1 0% !important;
    }

    .reveal .slide-text-container {
      position: relative !important;
      top: auto !important;
      left: auto !important;
      transform: none !important;
      width: 100% !important;
      max-width: 90% !important;
      box-sizing: border-box !important;
      padding: 0 80px !important; /* ~10% padding */
      margin: 0 auto !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      text-align: center !important;
    }

    /* Slide Typography (Rule 6: fill cell as much as possible) */
    .reveal {
      --h1-font-size: 100px !important;
      --h2-font-size: 72px !important;
      --h2-font-size-small: 56px !important;
      --font-size-l: 32px !important;
      --font-size-m: 26px !important;
      --font-size-body: 26px !important;
    }

    .reveal h1, .reveal .kp-h1 {
      font-size: 100px !important;
      line-height: 1.1 !important;
      font-weight: 700 !important;
      margin-bottom: 24px !important;
    }
    .reveal h2, .reveal .kp-h2 {
      font-size: 72px !important;
      line-height: 1.15 !important;
      font-weight: 700 !important;
      margin-bottom: 24px !important;
    }
    .reveal h2.small, .reveal .kp-h2.small {
      font-size: 56px !important;
    }
    .reveal h3, .reveal .kp-h3 {
      font-size: 48px !important;
      line-height: 1.2 !important;
      font-weight: 700 !important;
      margin-bottom: 20px !important;
    }
    .reveal p, .reveal li {
      font-size: 26px !important;
      line-height: 1.45 !important;
      margin-bottom: 16px !important;
    }
    .reveal .kp-body-large {
      font-size: 32px !important;
    }
    .reveal .kapr-eyebrow, .reveal .kapr-eyebrow-1 {
      font-weight: 300 !important;
      font-size: 24px !important;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      margin-bottom: 16px !important;
      display: block !important;
    }

    /* Hero Slide Sizing */
    .reveal .kapr-hero-1 h1 {
      font-size: 110px !important;
      line-height: 1.05 !important;
    }
    .reveal .kapr-hero-1 p {
      font-size: 36px !important;
    }

    /* Intro Slide Sizing */
    .reveal .kapr-brief h2 {
      font-size: 80px !important;
    }
    .reveal .kapr-brief p {
      font-size: 34px !important;
    }

    /* Light background overrides for headings and text that don't have explicit color classes */
    .reveal .slides section.slide-light-bg h1:not(.red):not(.magenta):not(.cream):not(.white-shadow),
    .reveal .slides section.slide-light-bg h2:not(.red):not(.magenta):not(.cream):not(.white-shadow),
    .reveal .slides section.slide-light-bg h3:not(.red):not(.magenta):not(.cream):not(.white-shadow),
    .reveal .slides section.slide-light-bg p:not(.kp-body-cream):not(.kp-body-gray):not(.kp-body-blue):not(.kp-body-darkblue) {
      color: #0d0a06 !important;
    }
    .reveal .slides section.slide-light-bg li {
      color: #0d0a06 !important;
    }
    .reveal .slides section.slide-light-bg .kapr-eyebrow,
    .reveal .slides section.slide-light-bg .kapr-eyebrow-1 {
      color: #0d0a06 !important;
    }

    /* Shift lists or columns slightly to prevent vertical overflow */
    .reveal .slide-column .slide-text-container {
      padding: 0 48px !important;
    }
    .reveal .kapr-rest .slide-text-container {
      padding: 0 32px !important;
    }
    .reveal .kapr-rest h2 {
      font-size: 40px !important;
      margin-bottom: 12px !important;
    }
    .reveal .kapr-rest .kapr-eyebrow {
      margin-bottom: 8px !important;
    }
    .reveal .kapr-rest p.kp-body-rest {
      font-size: 18px !important;
      line-height: 1.35 !important;
      margin-bottom: 12px !important;
    }
    .reveal .kapr-rest ol {
      font-size: 15px !important;
      line-height: 1.3 !important;
      text-align: left !important;
      margin-top: 0 !important;
      margin-bottom: 0 !important;
    }
    .reveal .kapr-rest li {
      font-size: 15px !important;
      margin-bottom: 6px !important;
    }

    /* Slide 14 About Vexy Lines specific styles */
    .reveal section.kapr-vl::before,
    .reveal section.kapr-vl::after {
      flex: 1 1 0% !important;
    }
    .reveal .kapr-vl .slide-text-container {
      max-width: 92% !important;
      padding: 0 40px !important;
    }
    .reveal .kapr-vl h2 { font-size: 72px !important; margin-bottom: 12px !important; }
    .reveal .kapr-vl .kapr-vl-lede { font-size: 28px !important; line-height: 1.35 !important; margin-bottom: 24px !important; }
    .reveal .kapr-vl .kapr-vl-cols {
      display: grid !important;
      grid-template-columns: 1fr 1fr 1fr !important;
      gap: 40px !important;
      margin-top: 16px !important;
      text-align: left !important;
    }
    .reveal .kapr-vl .kapr-vl-cols h3 { font-size: 32px !important; margin-bottom: 10px !important; margin-top: 0 !important; }
    .reveal .kapr-vl .kapr-vl-cols p { font-size: 22px !important; line-height: 1.4 !important; margin-bottom: 0 !important; }

    /* Badge overlays (1.5x larger, no margins) (Rule 2) */
    .reveal .slide-badge {
      z-index: 100 !important;
      box-sizing: border-box !important;
      padding: 40px 50px !important; /* 1.5x padding */
      border-radius: 16px !important;
      font-size: 26px !important; /* 1.5x font-size */
      line-height: 1.45 !important;
    }
    .reveal .slide-badge * {
      font-size: inherit !important;
      line-height: inherit !important;
      margin: 0 !important;
    }
    .reveal .slide-badge h3 {
      font-size: 36px !important;
      line-height: 1.2 !important;
      margin-top: 0 !important;
      margin-bottom: 12px !important;
    }
    .reveal .slide-badge p {
      font-size: 26px !important;
      line-height: 1.45 !important;
      margin-bottom: 0 !important;
    }
    .reveal .slide-badge span {
      font-size: 20px !important;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 12px !important;
      display: block !important;
    }

    /* Specific badge color palettes to preserve theme contrast */
    .reveal .kapr-bleed-card-1 {
      color: #0d0a06 !important;
      background-color: #f7eae1 !important;
    }
    .reveal .kapr-comp-b-card {
      color: #0d0a06 !important;
      background-color: #f7eae1 !important;
    }
    .reveal .kapr-comp-b-card h3 { color: #0d0a06 !important; }
    .reveal .kapr-comp-b-card p { color: #3a3a3a !important; }
    .reveal .kapr-comp-b-card span { color: #920796 !important; }

    .reveal .kapr-v1-ui-card {
      color: #fdf8ed !important;
      background-color: #37424f !important;
    }
    .reveal .kapr-v1-ui-card h3 { color: #fdf8ed !important; }
    .reveal .kapr-v1-ui-card p { color: #d0c8b8 !important; }
    .reveal .kapr-v1-ui-card span { color: #d6ff09 !important; }

    .reveal .kapr-v2-ui-card {
      color: #1651a5 !important;
      background-color: #fdf8ed !important;
      border: 1px solid #1651a5 !important;
    }
    .reveal .kapr-v2-ui-card h3 { color: #1651a5 !important; }
    .reveal .kapr-v2-ui-card p { color: #3b6fb6 !important; }
    .reveal .kapr-v2-ui-card span { color: #c80ace !important; }

    .reveal .kapr-v3-ui-card {
      color: #16110a !important;
      background-color: #d6ff09 !important;
    }
    .reveal .kapr-v3-ui-card h3 { color: #16110a !important; }
    .reveal .kapr-v3-ui-card p { color: #3c3325 !important; }
    .reveal .kapr-v3-ui-card span { color: #c80ace !important; }

    /* Theme color contrast overrides for standard columns */
    .reveal .kapr-prov-right { color: #000 !important; }
    .reveal .kapr-prov-right .kapr-eyebrow-1 { color: #333 !important; }
    .reveal .kapr-prov-right h2 { color: #000 !important; }
    .reveal .kapr-prov-right p { color: #222 !important; }

    .reveal .kapr-v1-left { color: #fdf8ed !important; }
    .reveal .kapr-v1-left .kapr-eyebrow { color: #d6ff09 !important; }
    .reveal .kapr-v1-left h2 { color: #fdf8ed !important; }
    .reveal .kapr-v1-left p { color: #fdf8ed !important; }

    .reveal .kapr-v2-right { color: #1651a5 !important; }
    .reveal .kapr-v2-right .kapr-eyebrow { color: #c80ace !important; }
    .reveal .kapr-v2-right h2 { color: #cd2426 !important; }
    .reveal .kapr-v2-right p { color: #1651a5 !important; }

    .reveal .kapr-v3-left { color: #16110a !important; }
    .reveal .kapr-v3-left .kapr-eyebrow { color: #c80ace !important; }
    .reveal .kapr-v3-left h2 { color: #111947 !important; }
    .reveal .kapr-v3-left p { color: #111947 !important; }

    /* Hide outer Webflow branding/menu elements and helper widgets */
    html body section.vx-menu-section, 
    html body .vx-footer-vlkapr, 
    html body vexy-menu, 
    html body vexy-footer,
    html body .w-webflow-badge,
    html body #freshworks-container,
    html body #freshworks-frame,
    html body iframe[id*="freshworks"],
    html body [class*="freshworks"] {
      display: none !important;
      visibility: hidden !important;
      opacity: 0 !important;
    }
    """
    soup.head.append(custom_style)

    # Add Reveal.js script and init logic
    reveal_js = soup.new_tag("script", src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.js")
    reveal_init = soup.new_tag("script")
    reveal_init.string = """
    document.addEventListener("DOMContentLoaded", function() {
      Reveal.initialize({
        width: 1440,
        height: 900,
        margin: 0,
        center: false,
        minScale: 0.2,
        maxScale: 2.0,
        hash: true,
        transition: 'slide'
      });
    });
    """
    
    if not soup.body:
        body = soup.new_tag("body")
        soup.append(body)
    soup.body.append(reveal_js)
    soup.body.append(reveal_init)

    # 6. Write output file
    output_dir = os.path.dirname(os.path.abspath(output))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    with open(output, "w", encoding="utf-8") as f:
        f.write(str(soup))
    print(f"Successfully converted and saved slide deck to: {output}")

    # 7. Start dev server
    if serve:
        print(f"Starting dev server in: {output_dir or '.'}")
        if output_dir:
            os.chdir(output_dir)
            
        handler = http.server.SimpleHTTPRequestHandler
        socketserver.TCPServer.allow_reuse_address = True
        
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"\n==========================================")
            print(f"  Slide deck is running at:")
            print(f"  http://localhost:{port}/")
            print(f"==========================================")
            print("Press Ctrl+C to stop the dev server.")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down dev server.")
                httpd.server_close()
