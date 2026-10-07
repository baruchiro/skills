def isCoderabbit: (.author.login // "" | ascii_downcase | contains("coderabbit"));

def threadOwner($marker):
  .comments.nodes as $c |
  if ($c[-1].body // "" | contains($marker)) then "you"
  elif (all($c[]; isCoderabbit)) and (any($c[]; any(.reactionGroups[]?; .content == "THUMBS_UP" and .viewerHasReacted)) | not) then "you"
  else "agent" end;

def checkName: .name // .context // "";

def checkState:
  if .status != null then
    if .status != "COMPLETED" then "pending"
    elif (.conclusion | IN("SUCCESS", "NEUTRAL", "SKIPPED")) then "ok"
    else "failed" end
  elif .state == "SUCCESS" then "ok"
  elif (.state | IN("PENDING", "EXPECTED")) then "pending"
  else "failed" end;

def skipPattern: "skip|base branch|target branch|paused|not enabled";

def classifyPr($marker):
  . as $pr |
  ($pr.reviewThreads.nodes | map(select(.isResolved | not) | threadOwner($marker))) as $owners |
  ($pr.commits.nodes[0].commit.statusCheckRollup.contexts.nodes // []) as $checks |
  ($checks | map(select(checkName | ascii_downcase | contains("coderabbit")))) as $crChecks |
  ($checks - $crChecks) as $ciChecks |
  ($pr.reviews.nodes | map(select(isCoderabbit))) as $crReviews |
  ($pr.comments.nodes | map(select(isCoderabbit))) as $crComments |
  ($crReviews | any(.commit.oid == $pr.headRefOid)) as $crReviewedHead |
  ($crChecks | any(checkState == "pending")) as $crRunning |
  ($crChecks | any(checkState == "ok")) as $crCheckOk |
  ($crComments | map(select(.body | test(skipPattern; "i"))) | last) as $skipComment |
  (if $pr.isDraft then "draft" else "ready" end) as $phase |
  def result($state; $next; $hint):
    {repo: $pr.repo, number: $pr.number, title: $pr.title, url: $pr.url, base: $pr.baseRefName,
     phase: $phase, status: ($phase + ":" + $state), next: $next, hint: $hint};
  if ($owners | any(. == "you")) then
    result("needs-you"; "you"; "\($owners | map(select(. == "you")) | length) open thread(s) waiting for your read, answer, 👍 or resolve")
  elif ($owners | any(. == "agent")) then
    result("needs-agent"; "claude"; "\($owners | map(select(. == "agent")) | length) open thread(s) for Claude to answer or fix")
  elif $pr.isDraft then
    result("clean"; "you"; "no open threads. Move to ready only if you reviewed all the files — file review marks are not visible to this report")
  elif ($ciChecks | any(checkState == "failed")) then
    result("ci-failing"; "claude"; "failed: \($ciChecks | map(select(checkState == "failed") | checkName) | join(", "))")
  elif $crRunning then
    result("cr-pending"; "wait"; "CodeRabbit is running")
  elif ($crReviewedHead or $crCheckOk) | not then
    if $skipComment != null then
      result("cr-not-triggered"; "claude"; "CodeRabbit did not review this head commit. Verify manually (base branch is likely not one CodeRabbit reviews); its comment: \($skipComment.body[0:400])")
    elif ($crReviews | length) > 0 then
      result("cr-pending"; "wait"; "CodeRabbit reviewed an older commit, not the current head yet")
    else
      result("cr-no-activity"; "claude"; "no CodeRabbit check, review or comment found. It may still be starting or never triggered. Verify manually: base branch, or comment `@coderabbitai review`")
    end
  elif ($ciChecks | any(checkState == "pending")) then
    result("ci-pending"; "wait"; "waiting for CI")
  else
    result("ready"; "merge"; "no open threads, CodeRabbit reviewed the head commit, CI green")
  end;
