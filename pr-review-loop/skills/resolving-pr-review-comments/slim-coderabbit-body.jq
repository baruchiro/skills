# Extracts CodeRabbit's "Prompt for AI Agents" block (plus its severity/tag
# line) from a comment body, to avoid feeding the full review prose into an
# agent's context. Falls back to the untouched body when that section is
# missing (e.g. summary comments, or CodeRabbit didn't generate one).
def slimCoderabbitBody:
  . as $body |
  ([$body | capture("<summary>🤖 Prompt for AI Agents</summary>\\s*```\\r?\\n(?<prompt>.*?)```"; "m")] | first) as $m |
  if $m == null then
    $body
  else
    ($body | split("\n")[0]) as $firstLine |
    (if ($firstLine | startswith("_")) then $firstLine + "\n\n" else "" end) + ($m.prompt | rtrimstr("\n"))
  end;
