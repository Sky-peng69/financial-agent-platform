--[[
Pandoc Lua filter to fix LTcaptype{none} issue.
Pandoc wraps tables in {\def\LTcaptype{none} ...} which breaks
when 'none' isn't a valid counter. We replace it with \let\LTcaptype\@empty.
--]]
function RawBlock(raw)
  if raw.format == 'latex' or raw.format == 'tex' then
    -- Fix: {\def\LTcaptype{none} -> {\let\LTcaptype\@empty
    raw.text = raw.text:gsub('{\\def\\LTcaptype{none}', '{\\let\\LTcaptype\\@empty')
    return raw
  end
end