# md2pdf — Markdown 到 PDF 转换脚本（接近 MPE 预览风格）

一个简单、实用的 Markdown→PDF 转换脚本，支持 Playwright 与 WeasyPrint 两种引擎，尽可能贴近 Trae 插件 “Markdown Preview Enhanced” 的预览效果。

## 特性

- 支持两种渲染引擎：`playwright`（无头浏览器，支持 JS）与 `weasyprint`（纯 HTML/CSS）。
- 支持 `Mermaid`、`MathJax`、`KaTeX`（需要 `playwright` 引擎）。
- 引入 GitHub Markdown CSS，并提供接近 MPE 的样式增强。
- 保留行内换行（启用 `nl2br` 扩展），避免段落合并。
- 针对多层级列表的预处理修复，保证嵌套层级与缩进正确。
- 可选封面（通过 `--cover` 指定另一 Markdown 作为首页）。

## 安装

```bash
git clone https://github.com/<your-username>/md2pdf.git
cd md2pdf

# 可选：创建全局命令（用户级软链）
ln -sf "$(pwd)/md2pdf.py" ~/.local/bin/md2pdf
export PATH="$HOME/.local/bin:$PATH"
```

> 首次运行脚本如果检测到缺少依赖，会自动在 `~/.md2pdf-venv` 创建用户级虚拟环境并安装必须库（`markdown`、`pymdown-extensions`、`playwright`、`weasyprint`），同时执行 `playwright install chromium`。后续使用无需重复安装。

## 使用

```bash
# 基本用法
md2pdf input.md

# 指定输出文件
md2pdf input.md -o out.pdf

# 指定引擎与主题
md2pdf input.md --engine playwright --theme mpe

# 添加封面与自定义样式
md2pdf input.md --cover cover.md --css custom.css

# 导出调试 HTML（便于排查列表结构、样式）
md2pdf input.md --debug-html
```

## 选项

- `--engine {auto|playwright|weasyprint}`
  - `auto`（默认）：优先使用 `playwright`，不可用时回退到 `weasyprint`。
  - `playwright`：使用无头 Chromium 渲染，可执行 JS，支持 Mermaid/MathJax/KaTeX、代码高亮、打印背景。
  - `weasyprint`：纯 HTML/CSS 渲染，不执行 JS；适合纯静态内容。

- `--theme {mpe|github|minimal}`
  - `mpe`（默认）：在 GitHub Markdown CSS 基础上，附加接近 MPE 的样式增强（标题、列表、blockquote、代码、打印）。
  - `github`：仅使用 GitHub Markdown CSS，干净一致的网页风格。
  - `minimal`：只应用脚本内置的基础样式（`DEFAULT_CSS`）。

- 其他常用：
  - `--math {none|mathjax|katex}`（默认 `mathjax`）
  - `--no-mermaid` 禁用 Mermaid
  - `--page-size`（Playwright）默认 `A4`
  - `--margin`（Playwright）默认 `20mm`（支持 `top right bottom left` 简写）
  - `--cover` 指定封面 Markdown
  - `--css` 注入额外 CSS
  - `--debug-html` 输出同名 `.html` 用于排查

## 注意

- 使用 `weasyprint` 时，JavaScript 不执行，因此 `Mermaid/MathJax/KaTeX` 不会渲染。
- 默认加载外部 CDN（highlight.js、github-markdown-css、mermaid、mathjax/katex），离线环境可在 README 中的链接位置改为自托管。
- 若遇到 PEP 668 “externally-managed” 提示，无需担心，脚本已内置用户级 venv 自举；也可以手动使用 `python -m venv ~/.md2pdf-venv` 并安装依赖。

## 许可

 MIT
