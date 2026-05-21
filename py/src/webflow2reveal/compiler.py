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
    class_specificity = {}
    
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
                # Basic specificity: count classes and IDs
                specificity = part.count('.') + part.count('#') * 10
                
                # Find class names like .kapr-brief
                classes_in_part = re.findall(r'\.([a-zA-Z0-9_-]+)', part)
                if classes_in_part:
                    # Apply color only to the last/most specific class in the compound selector
                    cls = classes_in_part[-1]
                    if specificity >= class_specificity.get(cls, 0):
                        class_colors[cls] = color
                        class_specificity[cls] = specificity
                        
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
    Resolves the background color for a list of classes, picking the most specific color.
    """
    for cls in reversed(classes):
        color = class_colors.get(cls)
        if color:
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

        # Inject default transition if not specified
        if not sec.get("data-transition"):
            sec["data-transition"] = "slide"

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
        elif len(layout_elements) > 2:
            for col in layout_elements:
                col_bg = get_section_bg_color(col.get("class", []), class_colors)
                if col_bg:
                    col['style'] = col.get('style', '') + f"; background-color: {col_bg} !important;"
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

def find_balanced_braces(text: str, start_idx: int) -> str:
    """
    Finds a balanced substring starting with '{' and ending with '}'.
    Handles strings with escaped characters and nested braces.
    """
    idx = text.find('{', start_idx)
    if idx == -1:
        return None
    
    brace_count = 0
    in_string = False
    string_char = None
    escaped = False
    
    for i in range(idx, len(text)):
        char = text[i]
        
        if escaped:
            escaped = False
            continue
            
        if char == '\\':
            escaped = True
            continue
            
        if char in ('"', "'", "`"):
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:
                in_string = False
                string_char = None
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[idx:i+1]
                    
    return None

def parse_options_from_js(js_content: str) -> dict:
    """
    Parses options from a JS content string where window.webflow2revealOptions is defined.
    """
    options = {}
    pattern = re.compile(r'webflow2revealOptions\s*=\s*')
    for match in pattern.finditer(js_content):
        start_idx = match.end()
        obj_text = find_balanced_braces(js_content, start_idx)
        if not obj_text:
            continue
            
        # Parse excludeSelectors
        exclude_selectors_match = re.search(r'excludeSelectors\s*:\s*(\[[^\]]*\]|"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\')', obj_text)
        if exclude_selectors_match:
            val_str = exclude_selectors_match.group(1).strip()
            if val_str.startswith('['):
                strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', val_str)
                selectors = []
                for d_match, s_match in strings:
                    if d_match:
                        selectors.append(d_match)
                    elif s_match:
                        selectors.append(s_match)
                options['excludeSelectors'] = selectors
            else:
                val_match = re.match(r'^["\'](.*)["\']$', val_str)
                if val_match:
                    options['excludeSelectors'] = [val_match.group(1)]
                    
        # Parse disableLayout
        disable_layout_match = re.search(r'disableLayout\s*:\s*(true|false)', obj_text, re.IGNORECASE)
        if disable_layout_match:
            options['disableLayout'] = disable_layout_match.group(1).lower() == 'true'
            
    return options

def extract_webflow2reveal_options(html_content: str, source_url: str = None) -> dict:
    """
    Scans the HTML page for inline and linked config scripts and extracts options.
    """
    options = {}
    soup = BeautifulSoup(html_content, "html.parser")
    
    inline_scripts = []
    external_script_urls = []
    
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            # Check if this looks like a configuration script
            # Do NOT pull down the main library package
            if ("reveal_config" in src or "vexy_lines_kapr_reveal_config" in src) and "webflow2revealjs" not in src:
                # Resolve relative URL
                if not src.startswith("http") and source_url and source_url.startswith("http"):
                    src = urljoin(source_url, src)
                elif src.startswith("//"):
                    src = "https:" + src
                external_script_urls.append(src)
        else:
            if script.string:
                inline_scripts.append(script.string)
                
    for script_content in inline_scripts:
        opts = parse_options_from_js(script_content)
        if opts:
            options.update(opts)
            
    for url in external_script_urls:
        try:
            print(f"Fetching config script: {url}")
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                opts = parse_options_from_js(resp.text)
                if opts:
                    options.update(opts)
        except Exception as e:
            print(f"Warning: Could not fetch config script from {url}: {e}")
            
    return options

def convert(source: str, output: str = "index.html", serve: bool = False, port: int = 8000, exclude: str = None):
    """
    Converts a Webflow page to a Reveal.js presentation.
    
    Args:
        source: The URL (http/https) or local file path of the Webflow page.
        output: The output file path for the generated slide deck.
        serve: Whether to start a local development server after conversion.
        port: The port for the development server (default 8000).
        exclude: Comma-separated list of CSS selectors to remove from the output presentation.
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

    # Extract options configured on the page
    page_options = extract_webflow2reveal_options(html_content, source_url=source if source.startswith("http") else None)
    if page_options:
        print(f"Extracted page configuration options: {page_options}")

    # Combine page excludeSelectors with CLI exclude
    all_excludes = []
    if exclude:
        all_excludes.extend([s.strip() for s in exclude.split(",") if s.strip()])
    
    if page_options and 'excludeSelectors' in page_options:
        all_excludes.extend(page_options['excludeSelectors'])
        
    # Remove excluded elements from the HTML soup
    if all_excludes:
        # Deduplicate
        all_excludes = list(dict.fromkeys(all_excludes))
        print(f"Applying exclusions: {all_excludes}")
        for selector in all_excludes:
            try:
                for el in soup.select(selector):
                    el.decompose()
            except Exception as e:
                print(f"Warning: Invalid selector for exclusion: {selector} ({e})", file=sys.stderr)

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

    # Find body background color as fallback for transparent slides
    body_bg = None
    if soup.body:
        body_bg = get_section_bg_color(soup.body.get("class", []), class_colors)

    # Determine background brightness and add slide-light-bg/slide-dark-bg classes
    for sec in sections:
        bg_color = sec.get("data-background-color")
        if bg_color:
            bg_color = bg_color.strip().lower()
            if bg_color in ('transparent', '#0000', 'rgba(0,0,0,0)', 'rgba(0, 0, 0, 0)'):
                bg_color = body_bg if body_bg else "#000000"
        
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
    
    # Check if reveal.css is already loaded, otherwise append
    reveal_css_found = False
    for link in soup.find_all("link"):
        if link.get("href") and "reveal" in link.get("href"):
            reveal_css_found = True
            break
    if not reveal_css_found:
        reveal_css = soup.new_tag("link", rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.css")
        soup.head.append(reveal_css)

    # Append custom styling overrides
    custom_style = soup.new_tag("style")
    custom_style.string = """
    /* Prevent window/body scroll breakout when reveal mode is active */
    html.reveal-mode:not(.reveal-scroll-active), body.reveal-mode:not(.reveal-scroll-active) {
      overflow: hidden !important;
      height: 100% !important;
      width: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
    }
    html.reveal-mode.reveal-scroll-active, body.reveal-mode.reveal-scroll-active {
      height: 100% !important;
      width: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
    }

    /* Presentation window baseline styles */
    .reveal {
      background-color: transparent !important;
      color: inherit;
      text-align: left;
      width: 100% !important;
      height: 100% !important;
    }
    .reveal .slide-background {
      background-color: transparent !important;
    }

    /* Revert Reveal's intrusive text styles under BYOL mode */
    .reveal.reveal-byol {
      color: inherit !important;
      text-align: inherit !important;
    }
    .reveal.reveal-byol .slides section {
      color: inherit !important;
      text-align: inherit !important;
    }

    .reveal-viewport {
      line-height: inherit !important;
    }

    /* Ensure slides cover the full viewport under disableLayout: true */
    .reveal .slides {
      width: 100% !important;
      height: 100% !important;
      inset: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
      max-width: none !important;
      max-height: none !important;
      text-align: inherit !important;
    }

    .reveal .slides section.slide-section {
      width: 100% !important;
      height: 100% !important;
      min-height: 0 !important;
      max-width: none !important;
      border-bottom: none !important;
      box-sizing: border-box !important;
      overflow: hidden !important;
      position: relative !important;
      padding: 0 !important;
      margin: 0 !important;
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

    /* Image containment rules */
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

    /* 3/5 vertical centering from bottom (= 40% from top) - disabled in BYOL mode */
    .reveal:not(.reveal-byol) section.slide-section:has(> .slide-text-container),
    .reveal:not(.reveal-byol) .slide-column:has(> .slide-text-container) {
      display: flex !important;
      flex-direction: column !important;
      box-sizing: border-box !important;
      padding-top: 40px !important;
      padding-bottom: 40px !important;
    }

    .reveal:not(.reveal-byol) section.slide-section:has(> .slide-text-container)::before,
    .reveal:not(.reveal-byol) .slide-column:has(> .slide-text-container)::before {
      content: "" !important;
      display: block !important;
      flex: 4 1 0% !important;
    }

    .reveal:not(.reveal-byol) section.slide-section:has(> .slide-text-container)::after,
    .reveal:not(.reveal-byol) .slide-column:has(> .slide-text-container)::after {
      content: "" !important;
      display: block !important;
      flex: 6 1 0% !important;
    }

    /* Align text layout containers to standard slide margins */
    .reveal:not(.reveal-byol) .slide-text-container {
      padding: 0 60px !important;
    }

    /* BYOL layout resets (Webflow styling overrides) */
    .reveal.reveal-byol .slide-text-container {
      width: 100% !important;
      max-width: none !important;
      margin: 0 !important;
    }

    .reveal .slide-badge {
      position: absolute !important;
      bottom: 40px !important;
      left: 40px !important;
      z-index: 10 !important;
    }

    /* Hide outer Webflow branding/menu elements and helper widgets */
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

    # Injected scripts
    reveal_js = soup.new_tag("script", src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.js")
    reveal_init = soup.new_tag("script")
    
    # Determine disableLayout value (defaulting to True if not specified or true, else respect page config)
    disable_layout_val = "true"
    if page_options and 'disableLayout' in page_options:
        disable_layout_val = "true" if page_options['disableLayout'] else "false"
        
    reveal_init.string = f"""
    document.addEventListener("DOMContentLoaded", function() {{
      // Capture original body background styles before Reveal.js overrides them
      const bodyStyles = window.getComputedStyle(document.body);
      const bgCol = bodyStyles.backgroundColor;
      const bgImg = bodyStyles.backgroundImage;
      const bgSize = bodyStyles.backgroundSize;
      const bgRepeat = bodyStyles.backgroundRepeat;
      const bgPos = bodyStyles.backgroundPosition;
      const bgAttachment = bodyStyles.backgroundAttachment;

      // Check if view=scroll is in the URL query string
      const urlParams = new URLSearchParams(window.location.search);
      const isScrollView = urlParams.get('view') === 'scroll';
      if (isScrollView) {{
        document.documentElement.classList.add('reveal-scroll-active');
        document.body.classList.add('reveal-scroll-active');
      }}

      Reveal.initialize({{
        width: 1440,
        height: 900,
        margin: 0,
        center: false,
        minScale: 0.2,
        maxScale: 2.0,
        hash: true,
        transition: 'slide',
        view: isScrollView ? 'scroll' : undefined,
        disableLayout: {disable_layout_val}
      }}).then(() => {{
        const revealEl = document.querySelector('.reveal');
        if (revealEl) {{
          revealEl.classList.add('reveal-byol');
        }}
        document.documentElement.classList.add('reveal-mode');
        document.body.classList.add('reveal-mode');

        // Restore body background styles to override Reveal's defaults
        if (bgCol) document.body.style.setProperty('background-color', bgCol, 'important');
        if (bgImg) document.body.style.setProperty('background-image', bgImg, 'important');
        if (bgSize) document.body.style.setProperty('background-size', bgSize, 'important');
        if (bgRepeat) document.body.style.setProperty('background-repeat', bgRepeat, 'important');
        if (bgPos) document.body.style.setProperty('background-position', bgPos, 'important');
        if (bgAttachment) document.body.style.setProperty('background-attachment', bgAttachment, 'important');
      }});
    }});
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
