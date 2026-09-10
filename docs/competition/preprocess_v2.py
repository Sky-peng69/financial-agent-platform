#!/usr/bin/env python3
"""Preprocess 策划书-弈金-v2.md for official competition format.

Transformations:
1. Extract # title → metadata
2. Shift ## → #, ### → ##
3. Standalone **N. xxx** → ### N. xxx (三级标题)
4. Clean up --- horizontal rules
"""
import re
import sys

INPUT = "/Users/laurence/Documents/金融agent/docs/competition/策划书-弈金-v2.md"
OUTPUT = "/Users/laurence/Documents/金融agent/docs/competition/策划书-弈金-v2-processed.md"


def process():
    with open(INPUT, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    title = ""
    i = 0

    # --- Extract title from first H1 ---
    while i < len(lines):
        line = lines[i]
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            i += 1
            break
        out_lines.append(line)
        i += 1

    # --- Process remaining lines ---
    while i < len(lines):
        line = lines[i]

        # Skip empty lines after title
        if title and not out_lines and line.strip() == "":
            i += 1
            continue

        # Shift heading levels: ## → #, ### → ##
        if line.startswith("### "):
            line = "##" + line[3:]
        elif line.startswith("## "):
            line = "#" + line[2:]

        # Convert standalone bold numbered paragraphs to H3 (###)
        # Pattern: **N. some text** at the start of a paragraph
        stripped = line.strip()
        if stripped.startswith("**") and stripped.endswith("**"):
            inner = stripped[2:-2]
            # Check if it starts with a number like "1." or "1、"
            if re.match(r"^\d+[\.\、]", inner):
                line = "### " + inner + "\n"

        # Remove standalone --- (horizontal rules), keep as blank line
        if stripped == "---":
            line = "\n"

        out_lines.append(line)
        i += 1

    # Write processed file
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    print(f"✓ Processed: {INPUT}")
    print(f"  → {OUTPUT}")
    print(f"  Title: {title}")
    print(f"  Lines: {len(lines)} → {len(out_lines)}")

    # Return title for pandoc metadata
    return title


if __name__ == "__main__":
    title = process()
    # Print title for use by shell script
    sys.stdout.write(f"TITLE={title}\n")