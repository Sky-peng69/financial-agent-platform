--[[
Pandoc Lua filter: Remove the {\def\LTcaptype{none} ... } wrapper
that pandoc puts around longtables. This wrapper uses \def\LTcaptype{none}
which doesn't work with basic TeX Live's longtable.
--]]
function RawBlock(el)
  if el.format:match('latex') then
    -- Remove the opening {\def\LTcaptype{none} ...
    el.text = el.text:gsub('{\\def\\LTcaptype{none} %% do not increment counter\n', '')
    -- Remove the trailing } that closes that group (after \end{longtable})
    el.text = el.text:gsub('\n}(%s*\\end{longtable})', '\n%1')
    el.text = el.text:gsub('(\\end{longtable})\n}', '%1\n')
  end
  return el
end
