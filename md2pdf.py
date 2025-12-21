#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
from pathlib import Path
import re


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_html(md_text: str, title: str, css_text: str, base_url: str, enable_math: str, enable_mermaid: bool, theme: str) -> str:
    try:
        import markdown as md
    except Exception:
        print("[ERROR] Missing dependency: markdown. Install via 'pip install markdown pymdown-extensions'", file=sys.stderr)
        sys.exit(1)

    extensions = [
        "extra",
        "toc",
        "codehilite",
        "fenced_code",
        "tables",
        "nl2br",
    ]
    extension_configs = {}
    try:
        import pymdownx  # noqa: F401
        extensions += [
            "pymdownx.superfences",
            "pymdownx.details",
            "pymdownx.tilde",
            "pymdownx.tasklist",
            "pymdownx.highlight",
        ]
        if enable_math != "none":
            extensions.append("pymdownx.arithmatex")
            extension_configs["pymdownx.arithmatex"] = {"generic": True}
    except Exception:
        pass

    body_html = md.markdown(md_text, extensions=extensions, extension_configs=extension_configs)

    highlight_css_href = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"
    highlight_js_src = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
    mermaid_js_src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js" if enable_mermaid else ""

    github_markdown_css_href = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css"

    mathjax_js = ""
    katex_css = ""
    katex_js = ""
    katex_auto_js = ""
    math_init = ""
    if enable_math == "mathjax":
        mathjax_js = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
        math_init = """
        <script>
        window.addEventListener('load', function(){
          if (window.MathJax && MathJax.typesetPromise) { MathJax.typesetPromise(); }
        });
        </script>
        """
    elif enable_math == "katex":
        katex_css = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css"
        katex_js = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"
        katex_auto_js = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
        math_init = """
        <script>
        window.addEventListener('load', function(){
          if (window.renderMathInElement) {
            renderMathInElement(document.body, {
              delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\]', display: true}
              ]
            });
          }
        });
        </script>
        """

    mermaid_init = """
    <script>
    function transformMermaidBlocks(){
      const blocks = Array.from(document.querySelectorAll('pre > code.language-mermaid'));
      for (const code of blocks) {
        const pre = code.parentElement;
        const div = document.createElement('div');
        div.className = 'mermaid';
        div.textContent = code.textContent;
        pre.replaceWith(div);
      }
    }
    window.addEventListener('load', function(){
      transformMermaidBlocks();
      if (window.mermaid) { mermaid.initialize({startOnLoad: true}); }
    });
    </script>
    """ if enable_mermaid else ""

    base_tag = f"<base href=\"{base_url}\">" if base_url else ""

    theme_links = ""
    theme_css = ""
    if theme in ("github", "mpe"):
        theme_links += f"<link rel=\"stylesheet\" href=\"{github_markdown_css_href}\">"
    if theme == "mpe":
        theme_css = MPE_CSS
    elif theme == "github":
        theme_css = ""
    else:
        theme_css = ""

    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>{title}</title>
        {base_tag}
        <link rel="stylesheet" href="{highlight_css_href}">
        {theme_links}
        <style>
        {DEFAULT_CSS}
        {theme_css}
        {css_text}
        </style>
      </head>
      <body>
        <main class="markdown-body">{body_html}</main>
        <script src="{highlight_js_src}"></script>
        <script>try{{hljs.highlightAll();}}catch(e){{}};</script>
        {f'<script src="{mermaid_js_src}"></script>' if mermaid_js_src else ''}
        {mermaid_init}
        {f'<script src="{mathjax_js}"></script>' if mathjax_js else ''}
        {f'<link rel="stylesheet" href="{katex_css}">' if katex_css else ''}
        {f'<script src="{katex_js}"></script>' if katex_js else ''}
        {f'<script src="{katex_auto_js}"></script>' if katex_auto_js else ''}
        {math_init}
      </body>
    </html>
    """
    return html


class Renderer:
    def render(self, html: str, output_path: Path, base_url: str, page_size: str, margin: str):
        raise NotImplementedError


class PlaywrightRenderer(Renderer):
    def render(self, html: str, output_path: Path, base_url: str, page_size: str, margin: str):
        from playwright.sync_api import sync_playwright

        margin_parts = [p.strip() for p in margin.split(" ") if p.strip()]
        m_top = margin_parts[0] if len(margin_parts) > 0 else "20mm"
        m_right = margin_parts[1] if len(margin_parts) > 1 else m_top
        m_bottom = margin_parts[2] if len(margin_parts) > 2 else m_top
        m_left = margin_parts[3] if len(margin_parts) > 3 else m_right

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            try:
                page.wait_for_function("window.MathJax && MathJax.typesetPromise", timeout=5000)
                page.evaluate("() => MathJax.typesetPromise()")
            except Exception:
                pass
            try:
                page.wait_for_function("window.mermaid && mermaid.initialize", timeout=5000)
                page.evaluate("() => { try { if (window.mermaid) { mermaid.run(); } } catch(e){} }")
            except Exception:
                pass
            pdf_bytes = page.pdf(format=page_size, margin={
                "top": m_top,
                "right": m_right,
                "bottom": m_bottom,
                "left": m_left,
            }, print_background=True)
            browser.close()
        output_path.write_bytes(pdf_bytes)


class WeasyPrintRenderer(Renderer):
    def render(self, html: str, output_path: Path, base_url: str, page_size: str, margin: str):
        from weasyprint import HTML
        HTML(string=html, base_url=base_url).write_pdf(str(output_path))


def select_renderer(preference: str) -> Renderer:
    if preference in (None, "", "auto"):
        try:
            import playwright  # noqa: F401
            return PlaywrightRenderer()
        except Exception:
            try:
                import weasyprint  # noqa: F401
                return WeasyPrintRenderer()
            except Exception:
                print("[ERROR] No PDF renderer available. Install 'playwright' or 'weasyprint'", file=sys.stderr)
                sys.exit(2)
    if preference == "playwright":
        try:
            import playwright  # noqa: F401
            return PlaywrightRenderer()
        except Exception:
            print("[ERROR] Playwright not installed. Install via 'pip install playwright' and run 'playwright install'", file=sys.stderr)
            sys.exit(2)
    if preference == "weasyprint":
        try:
            import weasyprint  # noqa: F401
            return WeasyPrintRenderer()
        except Exception:
            print("[ERROR] WeasyPrint not installed. Install via 'pip install weasyprint'", file=sys.stderr)
            sys.exit(2)
    print("[ERROR] Unknown engine preference", file=sys.stderr)
    sys.exit(2)


DEFAULT_CSS = """
@page { size: A4; margin: 20mm; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Liberation Sans', sans-serif; color: #24292e; }
.markdown-body { max-width: 900px; margin: 0 auto; padding: 0; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
.markdown-body pre { background: #f6f8fa; padding: 12px; overflow: auto; }
.markdown-body code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }
.page-break { page-break-before: always; }
img { max-width: 100%; }
table { border-collapse: collapse; }
table th, table td { border: 1px solid #d0d7de; padding: 6px 12px; }
"""

MPE_CSS = """
/* headings */
.markdown-body h1 { font-weight: 800; font-size: 2.0rem; }
.markdown-body h2 { font-weight: 700; font-size: 1.6rem; }
.markdown-body h3 { font-weight: 700; font-size: 1.25rem; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { margin-top: 1.2em; }

/* paragraph and list */
.markdown-body { line-height: 1.8; font-size: 16px; }
.markdown-body strong { font-weight: 700; }
.markdown-body ul, .markdown-body ol { margin: .6em 0; list-style-position: outside; }
.markdown-body ul { padding-left: 1.8rem; list-style-type: disc; }
.markdown-body ol { padding-left: 2.0rem; }
.markdown-body ol > li, .markdown-body ul > li { margin: .3em 0; }
.markdown-body ol ol, .markdown-body ol ul, .markdown-body ul ol, .markdown-body ul ul { margin: .2em 0; padding-left: 1.4rem; }
.markdown-body ul ul { list-style-type: circle; }
.markdown-body ul ul ul { list-style-type: square; }
.markdown-body li > p { margin: .2em 0; }
.markdown-body li::marker { font-weight: 700; }

/* blockquote similar to MPE */
.markdown-body blockquote { background: #f6f8fa; border-left: 4px solid #d0d7de; margin: 1em 0; padding: .6em 1em; }

/* code */
.markdown-body pre code { background: transparent; }
.markdown-body code { background: rgba(175,184,193,0.2); padding: .2em .4em; border-radius: 4px; }

/* hr */
.markdown-body hr { border: 0; border-top: 1px solid #d0d7de; margin: 1.5em 0; }

/* table */
.markdown-body table { width: 100%; }

/* print adjustments */
@media print {
  .markdown-body { color: #000; }
  a { color: inherit; text-decoration: none; }
}
"""

def fix_nested_lists(md_text: str) -> str:
    fence_re = re.compile(r"^\s*```")
    bullet_re = re.compile(r"^\s{2,}[*+-]\s+")
    top_bullet_re = re.compile(r"^[*+-]\s+")
    num_re = re.compile(r"^\s{2,}\d+[\.)]\s+")
    top_num_re = re.compile(r"^\d+[\.)]\s+")
    lines = md_text.splitlines()
    out = []
    in_code = False
    prev = ""
    for line in lines:
        if fence_re.match(line):
            in_code = not in_code
            out.append(line)
            prev = line
            continue
        is_nested = (not in_code) and (bullet_re.match(line) or num_re.match(line))
        is_top_bullet = (not in_code) and top_bullet_re.match(line)
        is_top_num = (not in_code) and top_num_re.match(line)
        need_blank = (is_nested or is_top_bullet or is_top_num) and prev.strip() != "" and not bullet_re.match(prev) and not num_re.match(prev) and not top_bullet_re.match(prev)
        if need_blank:
            out.append("")
        if (not in_code) and bullet_re.match(line):
            if top_num_re.match(prev):
                leading = len(re.match(r"^(\s+)", line).group(1)) if re.match(r"^(\s+)", line) else 0
                if leading < 6:
                    line = re.sub(r"^\s+", "      ", line)
        if (not in_code) and top_bullet_re.match(line):
            line = re.sub(r"^\*\s+", "- ", line)
        if (not in_code) and top_num_re.match(line):
            pass
        out.append(line)
        prev = line
    return "\n".join(out)


def main():
    venv_dir = Path.home() / ".md2pdf-venv"
    venv_python = venv_dir / "bin/python"
    if os.environ.get("MD2PDF_VENV_ACTIVE") != "1":
        try:
            import markdown  # noqa: F401
        except Exception:
            if not venv_python.exists():
                subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
                subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
                subprocess.run([str(venv_python), "-m", "pip", "install", "markdown", "pymdown-extensions", "playwright", "weasyprint"], check=True)
                try:
                    subprocess.run([str(venv_python), "-m", "playwright", "install", "chromium"], check=True)
                except Exception:
                    pass
            env = dict(os.environ)
            env["MD2PDF_VENV_ACTIVE"] = "1"
            os.execve(str(venv_python), [str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:], env)
    parser = argparse.ArgumentParser(prog="md2pdf", description="Convert Markdown to PDF with browser or WeasyPrint backends")
    parser.add_argument("input", nargs="+", help="Input Markdown file(s)")
    parser.add_argument("-o", "--output", help="Output PDF file (only for single input file)")
    parser.add_argument("--title", help="Document title", default="Document")
    parser.add_argument("--css", help="Additional CSS file")
    parser.add_argument("--engine", choices=["auto", "playwright", "weasyprint"], default="auto", help="Render engine")
    parser.add_argument("--page-size", default="A4", help="Page size for Playwright")
    parser.add_argument("--margin", default="20mm", help="Margin for Playwright (CSS shorthand: top right bottom left)")
    parser.add_argument("--math", choices=["none", "mathjax", "katex"], default="mathjax", help="Enable math rendering")
    parser.add_argument("--no-mermaid", action="store_true", help="Disable mermaid rendering")
    parser.add_argument("--cover", help="Optional cover Markdown file")
    parser.add_argument("--theme", choices=["mpe", "github", "minimal"], default="mpe", help="Styling theme")
    parser.add_argument("--debug-html", action="store_true", help="Output intermediate HTML next to PDF")
    args = parser.parse_args()

    # Resolve CSS once
    css_text = ""
    if args.css:
        css_path = Path(args.css).resolve()
        if not css_path.exists():
            print(f"[ERROR] CSS not found: {css_path}", file=sys.stderr)
            sys.exit(1)
        css_text = read_text(css_path)

    # Resolve Cover once
    cover_part = ""
    if args.cover:
        cover_path = Path(args.cover).resolve()
        if not cover_path.exists():
            print(f"[ERROR] Cover not found: {cover_path}", file=sys.stderr)
            sys.exit(1)
        cover_part = read_text(cover_path) + "\n\n<div class=\"page-break\"></div>\n\n"

    # Select renderer once
    renderer = select_renderer(args.engine)
    if isinstance(renderer, WeasyPrintRenderer) and (args.math != "none" or not args.no_mermaid):
        print("[WARN] Using WeasyPrint: JavaScript-based features (Mermaid/MathJax/KaTeX) will not render.", file=sys.stderr)

    inputs = [Path(p).resolve() for p in args.input]
    if len(inputs) > 1 and args.output:
        print("[ERROR] The -o/--output argument is not supported when processing multiple files.", file=sys.stderr)
        sys.exit(1)

    for in_path in inputs:
        if not in_path.exists():
            print(f"[WARN] Input not found: {in_path}, skipping.", file=sys.stderr)
            continue

        if args.output:
            out_path = Path(args.output).resolve()
        else:
            out_path = in_path.with_suffix(".pdf")

        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        base_url = in_path.parent.as_uri()

        parts = []
        if cover_part:
            parts.append(cover_part)
        parts.append(read_text(in_path))
        md_text = "\n\n".join(parts)
        md_text = fix_nested_lists(md_text)

        html = build_html(md_text, args.title, css_text, base_url, args.math, not args.no_mermaid, args.theme)

        if args.debug_html:
            out_path.with_suffix(".html").write_text(html, encoding="utf-8")

        try:
            renderer.render(html, out_path, base_url, args.page_size, args.margin)
            print(f"[OK] PDF generated: {out_path}")
        except Exception as e:
            print(f"[ERROR] Failed to render {in_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
