#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/策划书-弈金-数字金融版.md"
TEMPLATE="$DIR/yijin-template.tex"
TEX="$DIR/策划书-弈金-数字金融版.tex"
OUTPUT="$DIR/策划书-弈金-数字金融版.pdf"

cd "$DIR"
pandoc "$SRC" -o "$TEX" \
  --template="$TEMPLATE" \
  --from=markdown+smart \
  --metadata title="弈金：面向银行投研场景的可追溯上市公司智能研究工作台" \
  --pdf-engine=xelatex

xelatex -interaction=nonstopmode -halt-on-error "$TEX" > /dev/null
xelatex -interaction=nonstopmode -halt-on-error "$TEX" > /dev/null
xelatex -interaction=nonstopmode -halt-on-error "$TEX" > /dev/null

echo "完成: $OUTPUT ($(pdfinfo "$OUTPUT" | awk '/Pages:/ {print $2}') 页)"
