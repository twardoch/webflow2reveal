"use strict";
var Webflow2Reveal = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // src/index.ts
  var index_exports = {};
  __export(index_exports, {
    CUSTOM_CSS_OVERRIDE: () => CUSTOM_CSS_OVERRIDE,
    convertToReveal: () => convertToReveal,
    getSectionBgColor: () => getSectionBgColor,
    isSlideSection: () => isSlideSection,
    normalizeRevealDom: () => normalizeRevealDom,
    parseCssBackgroundColors: () => parseCssBackgroundColors,
    wrapContentsInDiv: () => wrapContentsInDiv
  });
  function parseCssBackgroundColors(cssContent) {
    const classColors = {};
    cssContent = cssContent.replace(/\/\*[\s\S]*?\*\//g, "");
    let depth = 0;
    let selectorBuffer = "";
    let rulesBuffer = "";
    const classSpecificity = {};
    function processBlock(selector, rules) {
      selector = selector.trim();
      rules = rules.trim();
      if (rules.includes("{")) {
        Object.assign(classColors, parseCssBackgroundColors(rules));
        return;
      }
      const bgColorPattern = /background-color:\s*([^;!\s]+)/i;
      const bgPattern = /\bbackground:\s*([^;!]+)/i;
      let color = null;
      const bgColorMatch = bgColorPattern.exec(rules);
      const bgMatch = bgPattern.exec(rules);
      if (bgColorMatch) {
        color = bgColorMatch[1].trim();
      } else if (bgMatch) {
        const val = bgMatch[1].trim();
        if (val.startsWith("#") || ["red", "blue", "green", "white", "black", "transparent"].includes(val) || val.startsWith("rgb")) {
          color = val;
        }
      }
      if (color) {
        const parts = selector.split(",");
        for (let part of parts) {
          part = part.trim();
          const specificity = (part.match(/\./g) || []).length + (part.match(/#/g) || []).length * 10;
          const classRegex = /\.([a-zA-Z0-9_-]+)/g;
          let classMatch;
          const classesInPart = [];
          while ((classMatch = classRegex.exec(part)) !== null) {
            classesInPart.push(classMatch[1]);
          }
          if (classesInPart.length > 0) {
            const cls = classesInPart[classesInPart.length - 1];
            if (specificity >= (classSpecificity[cls] || 0)) {
              classColors[cls] = color;
              classSpecificity[cls] = specificity;
            }
          }
        }
      }
    }
    for (let i = 0; i < cssContent.length; i++) {
      const char = cssContent[i];
      if (char === "{") {
        depth++;
        if (depth > 1) {
          rulesBuffer += char;
        }
      } else if (char === "}") {
        depth--;
        if (depth === 0) {
          processBlock(selectorBuffer, rulesBuffer);
          selectorBuffer = "";
          rulesBuffer = "";
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
  function isSlideSection(section) {
    const classes = Array.from(section.classList);
    const classesStr = classes.join(" ").toLowerCase();
    if (["menu", "nav", "footer", "header", "banner"].some((k) => classesStr.includes(k))) {
      return false;
    }
    if (section.id === "top" || section.id === "summary") {
      return false;
    }
    if (section.querySelector("vexy-menu") || section.querySelector("vexy-footer")) {
      return false;
    }
    return true;
  }
  function getSectionBgColor(classes, classColors) {
    for (let i = classes.length - 1; i >= 0; i--) {
      const cls = classes[i];
      const color = classColors[cls];
      if (color) {
        return color;
      }
    }
    return null;
  }
  function wrapContentsInDiv(parent, wrapperClass) {
    const doc = parent.ownerDocument;
    const wrapper = doc.createElement("div");
    wrapper.className = wrapperClass;
    const children = Array.from(parent.childNodes);
    const toWrap = [];
    const toKeep = [];
    for (const child of children) {
      if (child.nodeName.toLowerCase() === "script" || child.nodeName.toLowerCase() === "style") {
        toKeep.push(child);
      } else if (child.nodeType === Node.ELEMENT_NODE && Array.from(child.classList).some((cls) => ["mask", "video-wrap", "hover-video"].some((k) => cls.toLowerCase().includes(k)))) {
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
  function normalizeRevealDom(root, classColors) {
    const sections = Array.from(root.getElementsByTagName("section")).filter(isSlideSection);
    for (const sec of sections) {
      sec.classList.add("slide-section");
      const secBg = getSectionBgColor(Array.from(sec.classList), classColors);
      if (secBg && !sec.getAttribute("data-background-color")) {
        sec.setAttribute("data-background-color", secBg);
      }
      let badgeEl = null;
      const divs = Array.from(sec.getElementsByTagName("div"));
      const cardDivs = divs.filter((div) => {
        const cls = Array.from(div.classList).join(" ").toLowerCase();
        return cls.includes("card") || cls.includes("badge");
      });
      if (cardDivs.length === 1) {
        badgeEl = cardDivs[0];
      } else if (cardDivs.length > 1) {
        const kaprCards = cardDivs.filter((div) => {
          const cls = Array.from(div.classList).join(" ").toLowerCase();
          return cls.includes("kapr-");
        });
        if (kaprCards.length === 1) {
          badgeEl = kaprCards[0];
        }
      }
      if (badgeEl) {
        badgeEl.classList.add("slide-badge");
        const imgs = Array.from(sec.getElementsByTagName("img"));
        for (const img of imgs) {
          img.classList.add("slide-image-cover");
          if (img.parentElement) {
            img.parentElement.classList.add("slide-image-container");
          }
        }
        continue;
      }
      const directChildren = [];
      for (let i = 0; i < sec.children.length; i++) {
        const child = sec.children[i];
        if (child.tagName.toLowerCase() === "div" || child.tagName.toLowerCase() === "section") {
          const classesStr = Array.from(child.classList).join(" ").toLowerCase();
          if (!["menu", "nav", "footer", "mask", "header", "banner"].some((k) => classesStr.includes(k))) {
            directChildren.push(child);
          }
        }
      }
      let gridWrapper = null;
      let layoutElements = directChildren;
      if (directChildren.length === 1) {
        const wrapper = directChildren[0];
        const wrapperClasses = Array.from(wrapper.classList).join(" ").toLowerCase();
        if (["grid", "container", "row", "wrap", "bleed"].some((k) => wrapperClasses.includes(k))) {
          const wrapperChildren = [];
          for (let i = 0; i < wrapper.children.length; i++) {
            const sub = wrapper.children[i];
            if (sub.tagName.toLowerCase() === "div" || sub.tagName.toLowerCase() === "section") {
              const subClasses = Array.from(sub.classList).join(" ").toLowerCase();
              if (!["mask", "video-wrap", "hover-video"].some((k) => subClasses.includes(k))) {
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
        parentContainer.classList.add("slide-split-layout");
        for (const col of layoutElements) {
          col.classList.add("slide-column");
          const colBg = getSectionBgColor(Array.from(col.classList), classColors);
          if (colBg) {
            col.style.setProperty("background-color", colBg, "important");
          }
          const imgEl2 = col.querySelector("img");
          if (imgEl2) {
            col.classList.add("slide-image-container");
            imgEl2.classList.add("slide-image-cover");
          } else {
            let textWrapper = null;
            const children = Array.from(col.children).filter((c) => c.tagName.toLowerCase() === "div");
            if (children.length === 1 && Array.from(children[0].classList).some((cls) => ["text", "head"].some((k) => cls.toLowerCase().includes(k)))) {
              textWrapper = children[0];
            }
            if (textWrapper) {
              textWrapper.classList.add("slide-text-container");
            } else {
              wrapContentsInDiv(col, "slide-text-container");
            }
          }
        }
        continue;
      } else if (layoutElements.length > 2) {
        for (const col of layoutElements) {
          const colBg = getSectionBgColor(Array.from(col.classList), classColors);
          if (colBg) {
            col.style.setProperty("background-color", colBg, "important");
          }
        }
        continue;
      }
      const imgEl = sec.querySelector("img");
      const hasText = sec.querySelector("h1, h2, h3, p") !== null;
      if (imgEl && !hasText) {
        const parent = imgEl.parentElement;
        if (parent) {
          parent.classList.add("slide-image-container");
        }
        imgEl.classList.add("slide-image-cover");
      } else {
        let textWrapper = null;
        const divs2 = Array.from(sec.getElementsByTagName("div"));
        for (const div of divs2) {
          const divClasses = Array.from(div.classList).join(" ").toLowerCase();
          if (["hero-wrap", "container", "front"].some((k) => divClasses.includes(k))) {
            textWrapper = div;
            break;
          }
        }
        if (textWrapper) {
          textWrapper.classList.add("slide-text-container");
        } else {
          wrapContentsInDiv(sec, "slide-text-container");
        }
      }
    }
  }
  var CUSTOM_CSS_OVERRIDE = `
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
  background-color: revert;
  color: inherit;
  text-align: left;
  width: 100% !important;
  height: 100% !important;
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

.reveal:not(.reveal-byol) .slide-text-container {
  position: relative !important;
  top: auto !important;
  left: auto !important;
  transform: none !important;
  width: 100% !important;
  max-width: 90% !important;
  box-sizing: border-box !important;
  padding: 0 10% !important; /* Generic ~10% padding */
  margin: 0 auto !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  flex-shrink: 0 !important;
}

/* Basic text container for BYOL mode to avoid forcing flex centering */
.reveal.reveal-byol .slide-text-container {
  position: relative !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

/* Generic Badge overlays */
.reveal .slide-badge {
  z-index: 100 !important;
  box-sizing: border-box !important;
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
  async function convertToReveal(options) {
    const target = options.targetElement || document.body;
    let htmlContent = options.htmlContent || "";
    const isInPlace = !htmlContent && !options.sourceUrl;
    const bodyStyles = window.getComputedStyle(document.body);
    const bgCol = bodyStyles.backgroundColor;
    const bgImg = bodyStyles.backgroundImage;
    const bgSize = bodyStyles.backgroundSize;
    const bgRepeat = bodyStyles.backgroundRepeat;
    const bgPos = bodyStyles.backgroundPosition;
    const bgAttachment = bodyStyles.backgroundAttachment;
    if (!htmlContent && options.sourceUrl) {
      console.log(`Fetching Webflow page content from: ${options.sourceUrl}`);
      const fetchUrl = options.corsProxy ? options.corsProxy + encodeURIComponent(options.sourceUrl) : options.sourceUrl;
      const resp = await fetch(fetchUrl);
      if (!resp.ok) {
        throw new Error(`Failed to fetch Webflow source page. Status: ${resp.status}`);
      }
      htmlContent = await resp.text();
    }
    const classColors = {};
    if (isInPlace) {
      for (let i = 0; i < document.styleSheets.length; i++) {
        const sheet = document.styleSheets[i];
        try {
          const rules = sheet.cssRules || sheet.rules;
          if (rules) {
            for (let j = 0; j < rules.length; j++) {
              const rule = rules[j];
              if (rule.selectorText && rule.style) {
                const bgColor = rule.style.backgroundColor || rule.style.background;
                if (bgColor && !["transparent", "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)", "initial", "inherit"].includes(bgColor)) {
                  const parts = rule.selectorText.split(",");
                  for (let part of parts) {
                    part = part.trim();
                    const classRegex = /\.([a-zA-Z0-9_-]+)/g;
                    let classMatch;
                    while ((classMatch = classRegex.exec(part)) !== null) {
                      classColors[classMatch[1]] = bgColor;
                    }
                  }
                }
              }
            }
          }
        } catch (e) {
        }
      }
    }
    const doc = isInPlace ? document : new DOMParser().parseFromString(htmlContent, "text/html");
    let selectors = [];
    if (options.excludeSelectors) {
      if (Array.isArray(options.excludeSelectors)) {
        selectors = options.excludeSelectors;
      } else if (typeof options.excludeSelectors === "string") {
        selectors = options.excludeSelectors.split(",").map((s) => s.trim()).filter(Boolean);
      }
    }
    if (selectors.length > 0) {
      for (const selector of selectors) {
        try {
          const elList = doc.querySelectorAll(selector);
          elList.forEach((el) => el.remove());
        } catch (err) {
          console.warn(`Warning: Invalid selector for exclusion: ${selector}`, err);
        }
      }
    }
    const styleTags = Array.from(doc.getElementsByTagName("style"));
    for (const style of styleTags) {
      if (style.textContent) {
        Object.assign(classColors, parseCssBackgroundColors(style.textContent));
      }
    }
    const linkTags = Array.from(doc.querySelectorAll('link[rel="stylesheet"]'));
    for (const link of linkTags) {
      const href = link.getAttribute("href");
      if (!href) continue;
      let cssUrl = href;
      if (href.startsWith("//")) {
        cssUrl = "https:" + href;
      } else if (!href.startsWith("http") && options.sourceUrl) {
        cssUrl = new URL(href, options.sourceUrl).href;
      } else if (!href.startsWith("http")) {
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
    let revealDiv = doc.querySelector("div.reveal");
    let slidesDiv = doc.querySelector("div.reveal > div.slides");
    if (!revealDiv || !slidesDiv) {
      const allSections = Array.from(doc.getElementsByTagName("section"));
      const sections = allSections.filter(isSlideSection);
      revealDiv = document.createElement("div");
      revealDiv.className = "reveal";
      slidesDiv = document.createElement("div");
      slidesDiv.className = "slides";
      revealDiv.appendChild(slidesDiv);
      for (const sec of sections) {
        const secNode = isInPlace ? sec.cloneNode(true) : sec;
        slidesDiv.appendChild(secNode);
      }
    }
    normalizeRevealDom(revealDiv, classColors);
    let bodyBg = null;
    if (document.body) {
      bodyBg = getSectionBgColor(Array.from(document.body.classList), classColors);
    }
    const finalSections = Array.from(slidesDiv.getElementsByTagName("section"));
    for (const sec of finalSections) {
      let bg = sec.getAttribute("data-background-color");
      if (bg) {
        bg = bg.trim().toLowerCase();
        if (["transparent", "#0000", "rgba(0,0,0,0)", "rgba(0, 0, 0, 0)"].includes(bg)) {
          bg = bodyBg || "#000000";
        }
      }
      if (bg) {
        const bgVal = bg.trim().toLowerCase();
        let isLight = false;
        if (bgVal.startsWith("#")) {
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
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            if (luminance > 0.6) {
              isLight = true;
            }
          } catch (_) {
          }
        } else if (bgVal.startsWith("rgb")) {
          const parts = bgVal.match(/\d+/g);
          if (parts && parts.length >= 3) {
            const r = parseInt(parts[0], 10);
            const g = parseInt(parts[1], 10);
            const b = parseInt(parts[2], 10);
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            if (luminance > 0.6) {
              isLight = true;
            }
          }
        } else if (["white", "yellow", "cyan", "lime"].includes(bgVal)) {
          isLight = true;
        }
        if (isLight) {
          sec.classList.add("slide-light-bg");
        } else {
          sec.classList.add("slide-dark-bg");
        }
      }
    }
    if (isInPlace && target === document.body) {
      const isScrollView = new URLSearchParams(window.location.search).get("view") === "scroll";
      if (isScrollView) {
        document.documentElement.classList.add("reveal-scroll-active");
        document.body.classList.add("reveal-scroll-active");
      }
      document.documentElement.classList.add("reveal-mode");
      document.body.classList.add("reveal-mode");
      document.body.appendChild(revealDiv);
      if (!document.querySelector(".webflow2reveal-close")) {
        const closeBtn = document.createElement("div");
        closeBtn.className = "webflow2reveal-close";
        closeBtn.innerHTML = "&times;";
        closeBtn.addEventListener("click", () => {
          const url = new URL(window.location.href);
          url.searchParams.delete("reveal");
          url.searchParams.delete("view");
          window.location.href = url.pathname + url.search;
        });
        document.body.appendChild(closeBtn);
      }
    } else {
      target.innerHTML = "";
      target.appendChild(revealDiv);
    }
    let styleEl = document.head.querySelector("#webflow2reveal-styles");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "webflow2reveal-styles";
      document.head.appendChild(styleEl);
    }
    let dynamicBodyStyle = "";
    if (bgCol) dynamicBodyStyle += `background-color: ${bgCol} !important;
`;
    if (bgImg) dynamicBodyStyle += `background-image: ${bgImg} !important;
`;
    if (bgSize) dynamicBodyStyle += `background-size: ${bgSize} !important;
`;
    if (bgRepeat) dynamicBodyStyle += `background-repeat: ${bgRepeat} !important;
`;
    if (bgPos) dynamicBodyStyle += `background-position: ${bgPos} !important;
`;
    if (bgAttachment) dynamicBodyStyle += `background-attachment: ${bgAttachment} !important;
`;
    styleEl.textContent = CUSTOM_CSS_OVERRIDE + `
    body.reveal-viewport {
      ${dynamicBodyStyle}
    }
  `;
    if (!document.head.querySelector('link[href*="reveal.min.css"]')) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.css";
      document.head.appendChild(link);
    }
    if (options.onBeforeInit) {
      options.onBeforeInit();
    }
    const runInit = () => {
      if (typeof Reveal !== "undefined") {
        const isScrollView = new URLSearchParams(window.location.search).get("view") === "scroll";
        const defaultRevealOptions = {
          width: 1440,
          height: 900,
          margin: 0,
          center: false,
          minScale: 0.2,
          maxScale: 2,
          hash: true,
          transition: "slide",
          backgroundTransition: "slide",
          view: isScrollView ? "scroll" : void 0,
          disableLayout: true
        };
        const mergedRevealOptions = {
          ...defaultRevealOptions,
          ...options.revealOptions || {}
        };
        Reveal.initialize(mergedRevealOptions).then(() => {
          if (mergedRevealOptions.disableLayout) {
            const revealEl = document.querySelector(".reveal");
            if (revealEl) {
              revealEl.classList.add("reveal-byol");
            }
          }
          document.documentElement.classList.add("reveal-mode");
          document.body.classList.add("reveal-mode");
          if (options.onAfterInit) {
            options.onAfterInit();
          }
        });
      } else {
        console.error("Reveal.js failed to load.");
      }
    };
    if (typeof Reveal !== "undefined") {
      runInit();
    } else {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.js";
      script.onload = runInit;
      document.body.appendChild(script);
    }
  }
  if (typeof window !== "undefined") {
    const init = () => {
      const params = new URLSearchParams(window.location.search);
      if (params.get("reveal") === "1" || params.get("reveal") === "true") {
        const globalOpts = window.webflow2revealOptions || {};
        convertToReveal(globalOpts).catch((err) => {
          console.error("Failed to auto-convert to Reveal:", err);
        });
      }
      document.addEventListener("click", (e) => {
        const target = e.target;
        const trigger = target.closest("[data-w2r-trigger], .w2r-trigger, #w2r-trigger");
        if (trigger) {
          e.preventDefault();
          const url = new URL(window.location.href);
          url.searchParams.set("reveal", "1");
          window.history.pushState({}, "", url.pathname + url.search + url.hash);
          const globalOpts = window.webflow2revealOptions || {};
          convertToReveal(globalOpts).catch((err) => {
            console.error("Failed to convert to Reveal:", err);
          });
        }
      });
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  }
  return __toCommonJS(index_exports);
})();
