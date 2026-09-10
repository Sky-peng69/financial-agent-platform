"use client";

import type { SearchReference } from "@/lib/api";

/**
 * 展示 DeepSeek 联网搜索的参考来源列表。
 * 金融分析场景：可追溯性是专业感的核心要素。
 */
export default function SearchReferences({
  references,
}: {
  references: SearchReference[];
}) {
  if (!references || references.length === 0) return null;

  return (
    <div className="mt-4 border-t border-[#E5E7EB] pt-4">
      <h4 className="text-[#111827] text-xs font-semibold mb-3 flex items-center gap-2">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <polyline points="15 3 21 3 21 9" />
          <line x1="10" y1="14" x2="21" y2="3" />
        </svg>
        参考来源
        <span className="text-[#9CA3AF] font-normal">
          ({references.length})
        </span>
      </h4>
      <ul className="space-y-1.5">
        {references.map((ref, i) => {
          const title = ref.name || ref.title || `来源 ${i + 1}`;
          const url = ref.url || ref.link || "";
          const snippet = ref.snippet || ref.content || "";

          return (
            <li key={i} className="text-xs leading-relaxed">
              {url ? (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#2563EB] hover:text-[#1D4ED8] hover:underline transition-colors font-medium"
                >
                  {title}
                </a>
              ) : (
                <span className="text-[#374151] font-medium">{title}</span>
              )}
              {snippet && (
                <span className="text-[#9CA3AF] ml-1.5">— {snippet.slice(0, 150)}{snippet.length > 150 ? "..." : ""}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
