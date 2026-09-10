"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

/**
 * Custom table component that wraps each <table> in a scrollable container.
 * This enables:
 *  - border-radius (doesn't work on <table> display:table in browsers)
 *  - horizontal scrolling on narrow viewports
 *  - consistent border styling regardless of CSS cascade quirks
 */
function TableWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        overflowX: "auto",
        margin: "1.25rem 0",
        border: "1px solid #E5E7EB",
        borderRadius: "8px",
      }}
    >
      <table
        style={{
          width: "100%",
          minWidth: "100%",
          borderCollapse: "separate",
          borderSpacing: 0,
          fontSize: "0.875rem",
          border: "none",
          margin: 0,
        }}
      >
        {children}
      </table>
    </div>
  );
}

/** Resolve GFM alignment string (left/center/right/default) into CSS text-align */
function textAlign(align: string | null | undefined) {
  if (!align) return "left";
  if (align === "center") return "center";
  if (align === "right") return "right";
  return "left";
}

const markdownComponents: Partial<Components> = {
  table: ({ children }) => <TableWrapper>{children}</TableWrapper>,
  thead: ({ children }) => (
    <thead style={{ borderBottom: "2px solid rgba(37,99,235,0.2)" }}>
      {children}
    </thead>
  ),
  th: ({ children, style }) => (
    <th
      style={{
        background: "#F1F5F9",
        borderBottom: "1px solid #E5E7EB",
        borderRight: "1px solid #F3F4F6",
        padding: "0.75rem 1rem",
        textAlign: (style as any)?.textAlign || "left",
        color: "#1E40AF",
        fontSize: "0.75rem",
        fontWeight: 600,
        letterSpacing: "0.025em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </th>
  ),
  td: ({ children, style }) => (
    <td
      style={{
        borderBottom: "1px solid #F3F4F6",
        borderRight: "1px solid #F3F4F6",
        padding: "0.625rem 1rem",
        color: "#374151",
        fontSize: "0.875rem",
        lineHeight: 1.625,
        fontVariantNumeric: "tabular-nums",
        textAlign: (style as any)?.textAlign || "left",
      }}
    >
      {children}
    </td>
  ),
};

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
