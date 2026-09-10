#!/bin/bash
# 弈金策划书 PDF 生成脚本
# 用法: cd docs/competition && bash build-pdf.sh
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/策划书-弈金-v2.md"
TEMPLATE="$DIR/yijin-template.tex"
OUTPUT="$DIR/策划书-弈金-v2.pdf"
TEX="$DIR/策划书-弈金-v2.tex"

cd "$DIR"

echo "1. Pandoc: Markdown → LaTeX..."
pandoc "$SRC" -o "$TEX" \
  --template="$TEMPLATE" \
  --from=markdown+smart \
  --pdf-engine=xelatex

echo "2. 图片后期处理 — 去浮动 + 全宽嵌入..."
# 删掉 figure/centering/caption/endfigure 包装线
sed -i '' '/^\\begin{figure}$/d' "$TEX"
sed -i '' '/^\\centering$/d' "$TEX"
sed -i '' '/^\\end{figure}$/d' "$TEX"
sed -i '' '/^\\caption{/d' "$TEX"

# 只处理包含 pandocbounded+includegraphics 的行
# \pandocbounded{\includegraphics[keepaspectratio,alt={...}]{screenshots/X.png}}
#   → \begin{center}\n\includegraphics[width=\textwidth,keepaspectratio,alt={...}]{screenshots/X.png}\n\end{center}
sed -i '' '/\\pandocbounded{\\includegraphics/ {
  s/\\pandocbounded{\\includegraphics\[keepaspectratio/\\begin{center}\n\\includegraphics[width=\\textwidth,keepaspectratio/
  s/}}\s*$/}\n\\end{center}/
}' "$TEX"

echo "3. XeLaTeX 编译 (×3)..."
xelatex -interaction=nonstopmode -halt-on-error "$TEX" > /dev/null
xelatex -interaction=nonstopmode -halt-on-error "$TEX" > /dev/null
xelatex -interaction=nonstopmode -halt-on-error "$TEX" > /dev/null

echo "✅ 完成: $OUTPUT ($(pdfinfo "$OUTPUT" 2>/dev/null | grep Pages | awk '{print $2}') 页)"
