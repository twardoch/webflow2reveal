// this_file: js/src/index.ts

export interface ConvertOptions {
  /** The URL of the Webflow page to convert. If provided, the page content will be fetched. */
  sourceUrl?: string;
  /** The raw HTML content of the Webflow page. If provided, fetching sourceUrl is skipped. */
  htmlContent?: string;
  /** CORS proxy prefix to fetch cross-origin resources. E.g. "https://api.allorigins.win/raw?url=" */
  corsProxy?: string;
  /** The element to mount the reveal presentation inside. Defaults to document.body. */
  targetElement?: HTMLElement;
  /** Callback triggered before Reveal.initialize runs. */
  onBeforeInit?: () => void;
  /** Callback triggered after Reveal is initialized. */
  onAfterInit?: () => void;
}

export function parseCssBackgroundColors(cssContent: string): Record<string, string> {
  const classColors: Record<string, string> = {};
  
  // Clean comments first
  cssContent = cssContent.replace(/\/\*[\s\S]*?\*\//g, '');
  
  // Track open/close braces to parse blocks safely
  let depth = 0;
  let selectorBuffer = '';
  let rulesBuffer = '';
  
  function processBlock(selector: string, rules: string) {
    selector = selector.trim();
    rules = rules.trim();
    
    // If the rules block itself contains nested rules (like media queries), parse them recursively
    if (rules.includes('{')) {
      Object.assign(classColors, parseCssBackgroundColors(rules));
      return;
    }
    
    const bgColorPattern = /background-color:\s*([^;!\s]+)/i;
    const bgPattern = /\bbackground:\s*([^;!]+)/i;
    
    let color: string | null = null;
    const bgColorMatch = bgColorPattern.exec(rules);
    const bgMatch = bgPattern.exec(rules);
    
    if (bgColorMatch) {
      color = bgColorMatch[1].trim();
    } else if (bgMatch) {
      const val = bgMatch[1].trim();
      if (val.startsWith('#') || ['red', 'blue', 'green', 'white', 'black', 'transparent'].includes(val) || val.startsWith('rgb')) {
        color = val;
      }
    }
    
    if (color) {
      const parts = selector.split(',');
      for (let part of parts) {
        part = part.trim();
        const classRegex = /\.([a-zA-Z0-9_-]+)/g;
        let classMatch: RegExpExecArray | null;
        while ((classMatch = classRegex.exec(part)) !== null) {
          classColors[classMatch[1]] = color;
        }
      }
    }
  }
  
  for (let i = 0; i < cssContent.length; i++) {
    const char = cssContent[i];
    if (char === '{') {
      depth++;
      if (depth > 1) {
        rulesBuffer += char;
      }
    } else if (char === '}') {
      depth--;
      if (depth === 0) {
        processBlock(selectorBuffer, rulesBuffer);
        selectorBuffer = '';
        rulesBuffer = '';
      } else {
        rulesBuffer += char;
      }
    } else {
      if (depth === 0) {
        selectorBuffer += char;
      } else {
        rulesBuffer += char;
      }
    }
  }
  
  return classColors;
}

export function isSlideSection(section: HTMLElement): boolean {
  const classes = Array.from(section.classList);
  const classesStr = classes.join(' ').toLowerCase();
  
  // Filter out known header/footer/menu sections
  if (['menu', 'nav', 'footer', 'header', 'banner'].some(k => classesStr.includes(k))) {
    return false;
  }
  if (section.id === 'top' || section.id === 'summary') {
    return false;
  }
  if (section.querySelector('vexy-menu') || section.querySelector('vexy-footer')) {
    return false;
  }
  return true;
}

export function getSectionBgColor(classes: string[], classColors: Record<string, string>): string | null {
  for (let i = classes.length - 1; i >= 0; i--) {
    const cls = classes[i];
    const color = classColors[cls];
    if (color && !['transparent', '#0000', 'rgba(0,0,0,0)', 'rgba(0, 0, 0, 0)'].includes(color)) {
      return color;
    }
  }
  return null;
}

export function wrapContentsInDiv(parent: HTMLElement, wrapperClass: string): void {
  const doc = parent.ownerDocument;
  const wrapper = doc.createElement('div');
  wrapper.className = wrapperClass;
  
  const children = Array.from(parent.childNodes);
  const toWrap: ChildNode[] = [];
  const toKeep: ChildNode[] = [];
  
  for (const child of children) {
    if (child.nodeName.toLowerCase() === 'script' || child.nodeName.toLowerCase() === 'style') {
      toKeep.push(child);
    } else if (child.nodeType === Node.ELEMENT_NODE && 
               Array.from((child as HTMLElement).classList).some(cls => ['mask', 'video-wrap', 'hover-video'].some(k => cls.toLowerCase().includes(k)))) {
      toKeep.push(child);
    } else {
      toWrap.push(child);
    }
  }
  
  for (const child of toWrap) {
    wrapper.appendChild(child);
  }
  
  parent.appendChild(wrapper);
  for (const child of toKeep) {
    parent.appendChild(child);
  }
}

export function normalizeRevealDom(root: HTMLElement, classColors: Record<string, string>): void {
  const sections = Array.from(root.getElementsByTagName('section')).filter(isSlideSection);
  
  for (const sec of sections) {
    sec.classList.add('slide-section');
    
    const secBg = getSectionBgColor(Array.from(sec.classList), classColors);
    if (secBg && !sec.getAttribute('data-background-color')) {
      sec.setAttribute('data-background-color', secBg);
    }
    
    let badgeEl: HTMLElement | null = null;
    const divs = Array.from(sec.getElementsByTagName('div'));
    
    // Only detect as slide-badge if there is at most one card/badge in the section,
    // and it is a kapr-specific card or a single card slide layout.
    const cardDivs = divs.filter(div => {
      const cls = Array.from(div.classList).join(' ').toLowerCase();
      return cls.includes('card') || cls.includes('badge');
    });

    if (cardDivs.length === 1) {
      badgeEl = cardDivs[0];
    } else if (cardDivs.length > 1) {
      const kaprCards = cardDivs.filter(div => {
        const cls = Array.from(div.classList).join(' ').toLowerCase();
        return cls.includes('kapr-');
      });
      if (kaprCards.length === 1) {
        badgeEl = kaprCards[0];
      }
    }
    
    if (badgeEl) {
      badgeEl.classList.add('slide-badge');
      const imgs = Array.from(sec.getElementsByTagName('img'));
      for (const img of imgs) {
        img.classList.add('slide-image-cover');
        if (img.parentElement) {
          img.parentElement.classList.add('slide-image-container');
        }
      }
      continue;
    }
    
    // Look for layout children
    const directChildren: HTMLElement[] = [];
    for (let i = 0; i < sec.children.length; i++) {
      const child = sec.children[i] as HTMLElement;
      if (child.tagName.toLowerCase() === 'div' || child.tagName.toLowerCase() === 'section') {
        const classesStr = Array.from(child.classList).join(' ').toLowerCase();
        if (!['menu', 'nav', 'footer', 'mask', 'header', 'banner'].some(k => classesStr.includes(k))) {
          directChildren.push(child);
        }
      }
    }
    
    let gridWrapper: HTMLElement | null = null;
    let layoutElements = directChildren;
    if (directChildren.length === 1) {
      const wrapper = directChildren[0];
      const wrapperClasses = Array.from(wrapper.classList).join(' ').toLowerCase();
      if (['grid', 'container', 'row', 'wrap', 'bleed'].some(k => wrapperClasses.includes(k))) {
        const wrapperChildren: HTMLElement[] = [];
        for (let i = 0; i < wrapper.children.length; i++) {
          const sub = wrapper.children[i] as HTMLElement;
          if (sub.tagName.toLowerCase() === 'div' || sub.tagName.toLowerCase() === 'section') {
            const subClasses = Array.from(sub.classList).join(' ').toLowerCase();
            if (!['mask', 'video-wrap', 'hover-video'].some(k => subClasses.includes(k))) {
              wrapperChildren.push(sub);
            }
          }
        }
        if (wrapperChildren.length > 0) {
          gridWrapper = wrapper;
          layoutElements = wrapperChildren;
        }
      }
    }
    
    if (layoutElements.length === 2) {
      const parentContainer = gridWrapper ? gridWrapper : sec;
      parentContainer.classList.add('slide-split-layout');
      
      for (const col of layoutElements) {
        col.classList.add('slide-column');
        
        const colBg = getSectionBgColor(Array.from(col.classList), classColors);
        if (colBg) {
          col.style.setProperty('background-color', colBg, 'important');
        }
        
        const imgEl = col.querySelector('img');
        if (imgEl) {
          col.classList.add('slide-image-container');
          imgEl.classList.add('slide-image-cover');
        } else {
          let textWrapper: HTMLElement | null = null;
          const children = Array.from(col.children).filter(c => c.tagName.toLowerCase() === 'div') as HTMLElement[];
          if (children.length === 1 && Array.from(children[0].classList).some(cls => ['text', 'head'].some(k => cls.toLowerCase().includes(k)))) {
            textWrapper = children[0];
          }
          
          if (textWrapper) {
            textWrapper.classList.add('slide-text-container');
          } else {
            wrapContentsInDiv(col, 'slide-text-container');
          }
        }
      }
      continue;
    }
    
    const imgEl = sec.querySelector('img');
    const hasText = sec.querySelector('h1, h2, h3, p') !== null;
    if (imgEl && !hasText) {
      const parent = imgEl.parentElement;
      if (parent) {
        parent.classList.add('slide-image-container');
      }
      imgEl.classList.add('slide-image-cover');
    } else {
      let textWrapper: HTMLElement | null = null;
      const divs = Array.from(sec.getElementsByTagName('div'));
      for (const div of divs) {
        const divClasses = Array.from(div.classList).join(' ').toLowerCase();
        if (['hero-wrap', 'container', 'front'].some(k => divClasses.includes(k))) {
          textWrapper = div;
          break;
        }
      }
      if (textWrapper) {
        textWrapper.classList.add('slide-text-container');
      } else {
        wrapContentsInDiv(sec, 'slide-text-container');
      }
    }
  }
}

export const CUSTOM_CSS_OVERRIDE = `
/* Prevent window/body scroll breakout when reveal mode is active */
html.reveal-mode, body.reveal-mode {
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
  min-height: 0 !important;
  max-width: none !important;
  border-bottom: none !important;
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

/* Close button for reveal mode */
.webflow2reveal-close {
  position: fixed;
  top: 24px;
  right: 24px;
  width: 48px;
  height: 48px;
  background: rgba(15, 12, 8, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(252, 250, 247, 0.15);
  border-radius: 50%;
  color: #fcfaf7;
  font-size: 28px;
  font-weight: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 999999;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.webflow2reveal-close:hover {
  background: #d6ff09;
  color: #0d0a06;
  border-color: #d6ff09;
  transform: scale(1.08);
}
/* When in reveal mode, hide all other direct children of body */
body.reveal-mode > :not(.reveal):not(.webflow2reveal-close) {
  display: none !important;
}
`;

export async function convertToReveal(options: ConvertOptions): Promise<void> {
  const target = options.targetElement || document.body;
  let htmlContent = options.htmlContent || '';
  const isInPlace = !htmlContent && !options.sourceUrl;
  
  if (!htmlContent && options.sourceUrl) {
    console.log(`Fetching Webflow page content from: ${options.sourceUrl}`);
    const fetchUrl = options.corsProxy 
      ? options.corsProxy + encodeURIComponent(options.sourceUrl)
      : options.sourceUrl;
      
    const resp = await fetch(fetchUrl);
    if (!resp.ok) {
      throw new Error(`Failed to fetch Webflow source page. Status: ${resp.status}`);
    }
    htmlContent = await resp.text();
  }
  
  const classColors: Record<string, string> = {};

  // Extract colors from active stylesheets in-place
  if (isInPlace) {
    for (let i = 0; i < document.styleSheets.length; i++) {
      const sheet = document.styleSheets[i];
      try {
        const rules = sheet.cssRules || sheet.rules;
        if (rules) {
          for (let j = 0; j < rules.length; j++) {
            const rule = rules[j] as CSSStyleRule;
            if (rule.selectorText && rule.style) {
              const bgColor = rule.style.backgroundColor || rule.style.background;
              if (bgColor && !['transparent', 'rgba(0, 0, 0, 0)', 'rgba(0,0,0,0)', 'initial', 'inherit'].includes(bgColor)) {
                const parts = rule.selectorText.split(',');
                for (let part of parts) {
                  part = part.trim();
                  const classRegex = /\.([a-zA-Z0-9_-]+)/g;
                  let classMatch: RegExpExecArray | null;
                  while ((classMatch = classRegex.exec(part)) !== null) {
                    classColors[classMatch[1]] = bgColor;
                  }
                }
              }
            }
          }
        }
      } catch (e) {
        // Ignore CORS errors on stylesheet rule reading
      }
    }
  }

  const doc = isInPlace ? document : new DOMParser().parseFromString(htmlContent, 'text/html');

  // 1. Parse inline style tags
  const styleTags = Array.from(doc.getElementsByTagName('style'));
  for (const style of styleTags) {
    if (style.textContent) {
      Object.assign(classColors, parseCssBackgroundColors(style.textContent));
    }
  }

  // 2. Parse external link stylesheets
  const linkTags = Array.from(doc.querySelectorAll('link[rel="stylesheet"]')) as HTMLLinkElement[];
  for (const link of linkTags) {
    const href = link.getAttribute('href');
    if (!href) continue;

    let cssUrl = href;
    if (href.startsWith('//')) {
      cssUrl = 'https:' + href;
    } else if (!href.startsWith('http') && options.sourceUrl) {
      cssUrl = new URL(href, options.sourceUrl).href;
    } else if (!href.startsWith('http')) {
      cssUrl = new URL(href, window.location.href).href;
    }

    try {
      const fetchUrl = options.corsProxy ? options.corsProxy + encodeURIComponent(cssUrl) : cssUrl;
      const cssResp = await fetch(fetchUrl);
      if (cssResp.ok) {
        const text = await cssResp.text();
        Object.assign(classColors, parseCssBackgroundColors(text));
      }
    } catch (e) {
      console.warn(`Warning: Could not fetch stylesheet ${cssUrl}:`, e);
    }
  }

  // 3. Locate or scaffold Reveal container
  let revealDiv = doc.querySelector('div.reveal') as HTMLElement | null;
  let slidesDiv = doc.querySelector('div.reveal > div.slides') as HTMLElement | null;

  if (!revealDiv || !slidesDiv) {
    const allSections = Array.from(doc.getElementsByTagName('section'));
    const sections = allSections.filter(isSlideSection);

    revealDiv = document.createElement('div');
    revealDiv.className = 'reveal';
    slidesDiv = document.createElement('div');
    slidesDiv.className = 'slides';
    revealDiv.appendChild(slidesDiv);

    for (const sec of sections) {
      const secNode = isInPlace ? (sec.cloneNode(true) as HTMLElement) : sec;
      slidesDiv.appendChild(secNode);
    }
  }

  // 4. Normalize DOM structure inside reveal
  normalizeRevealDom(revealDiv, classColors);

  // 5. Determine background brightness light/dark styles
  const finalSections = Array.from(slidesDiv.getElementsByTagName('section'));
  for (const sec of finalSections) {
    const bg = sec.getAttribute('data-background-color');
    if (bg) {
      const bgVal = bg.trim().toLowerCase();
      let isLight = false;
      
      if (bgVal.startsWith('#')) {
        const hex = bgVal.substring(1);
        try {
          let r = 255, g = 255, b = 255;
          if (hex.length === 3) {
            r = parseInt(hex[0] + hex[0], 16);
            g = parseInt(hex[1] + hex[1], 16);
            b = parseInt(hex[2] + hex[2], 16);
          } else if (hex.length === 6) {
            r = parseInt(hex.substring(0, 2), 16);
            g = parseInt(hex.substring(2, 4), 16);
            b = parseInt(hex.substring(4, 6), 16);
          }
          const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0;
          if (luminance > 0.6) {
            isLight = true;
          }
        } catch (_) {}
      } else if (bgVal.startsWith('rgb')) {
        const parts = bgVal.match(/\d+/g);
        if (parts && parts.length >= 3) {
          const r = parseInt(parts[0], 10);
          const g = parseInt(parts[1], 10);
          const b = parseInt(parts[2], 10);
          const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0;
          if (luminance > 0.6) {
            isLight = true;
          }
        }
      } else if (['white', 'yellow', 'cyan', 'lime'].includes(bgVal)) {
        isLight = true;
      }

      if (isLight) {
        sec.classList.add('slide-light-bg');
      } else {
        sec.classList.add('slide-dark-bg');
      }
    }
  }

  // 6. Clear target container and mount
  if (isInPlace && target === document.body) {
    document.documentElement.classList.add('reveal-mode');
    document.body.classList.add('reveal-mode');
    document.body.appendChild(revealDiv);
    
    // Add close button
    if (!document.querySelector('.webflow2reveal-close')) {
      const closeBtn = document.createElement('div');
      closeBtn.className = 'webflow2reveal-close';
      closeBtn.innerHTML = '&times;';
      closeBtn.addEventListener('click', () => {
        const url = new URL(window.location.href);
        url.searchParams.delete('reveal');
        window.location.href = url.pathname + url.search;
      });
      document.body.appendChild(closeBtn);
    }
  } else {
    target.innerHTML = '';
    target.appendChild(revealDiv);
  }

  // 7. Inject styles
  if (!document.head.querySelector('#webflow2reveal-styles')) {
    const style = document.createElement('style');
    style.id = 'webflow2reveal-styles';
    style.textContent = CUSTOM_CSS_OVERRIDE;
    document.head.appendChild(style);
  }

  // Inject Reveal css stylesheet
  if (!document.head.querySelector('link[href*="reveal.min.css"]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.min.css';
    document.head.appendChild(link);
  }

  // 8. Inject scripts and initialize Reveal
  if (options.onBeforeInit) {
    options.onBeforeInit();
  }

  const runInit = () => {
    // @ts-ignore
    if (typeof Reveal !== 'undefined') {
      // @ts-ignore
      Reveal.initialize({
        width: 1440,
        height: 900,
        margin: 0,
        center: false,
        minScale: 0.2,
        maxScale: 2.0,
        hash: true,
        transition: 'slide'
      }).then(() => {
        if (options.onAfterInit) {
          options.onAfterInit();
        }
      });
    } else {
      console.error('Reveal.js failed to load.');
    }
  };

  // Check if Reveal is already loaded globally
  // @ts-ignore
  if (typeof Reveal !== 'undefined') {
    runInit();
  } else {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.5.0/reveal.js';
    script.onload = runInit;
    document.body.appendChild(script);
  }
}

// Auto-initialize on load if ?reveal=1 is in URL
if (typeof window !== 'undefined') {
  const init = () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('reveal') === '1' || params.get('reveal') === 'true') {
      convertToReveal({}).catch(err => {
        console.error('Failed to auto-convert to Reveal:', err);
      });
    }

    // Hook up click event on any element with data-w2r-trigger or class w2r-trigger
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const trigger = target.closest('[data-w2r-trigger], .w2r-trigger, #w2r-trigger');
      if (trigger) {
        e.preventDefault();
        const url = new URL(window.location.href);
        url.searchParams.set('reveal', '1');
        window.history.pushState({}, '', url.pathname + url.search + url.hash);
        convertToReveal({}).catch(err => {
          console.error('Failed to convert to Reveal:', err);
        });
      }
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}
