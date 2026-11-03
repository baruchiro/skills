# PR readiness verdict package regression checks

Run the offline evaluation-package checks from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

To also exercise the **actual, unmodified** Hermes scanner and installation policy:

```sh
HERMES_AGENT_ROOT=/path/to/hermes-agent python3 -m unittest discover -s tests -v
```

Use a Python environment compatible with that Hermes checkout. No dependency
installation, network request, skill installation, profile write, or fixture code
execution is performed. Without `HERMES_AGENT_ROOT`, the two guard integration
tests are explicitly skipped; an offline-only pass does not establish scanner
compatibility. Temporary copies use Python's temporary directory selection
(`TMPDIR` may be set to an isolated workspace).

## Why the evaluation wording matters

Issue [#7](https://github.com/baruchiro/skills/issues/7) was reproduced against
`skills-guard-v10`: a literal parent-directory escape targeting a sensitive OS
file in the hygiene scenario's **expected output** triggered critical
`system_passwd_access` and medium `path_traversal` findings. The scanner treats
that JSON text as bundle content, not as an inert review expectation. The
community-source policy hard-blocked it, even with force enabled.

The expected output now describes the same parent-directory escape and
out-of-root read without an unnecessary sensitive-file payload. The vulnerable
`path.resolve(EXPORT_ROOT, relativePath)` fixture and the explicit path-confinement
and symlink-resolution expectations remain. The skill instructions and all three
evaluation scenarios remain intact. Nothing is encoded, hidden behind ignore
rules, or exempted from scanning. Two informational agent-config references in
`SKILL.md` remain visible to the guard.

The guard tests scan the entire installable directory as a community source and
require installation policy to allow it **without force**. A negative control
restores the original example to a temporary copy and requires the same scanner
to reject it, including when force is requested. Test code stays outside the
installable directory so its negative control is not itself shipped with the
skill. This layout does not exclude any distributed file from the scanner.

This is an equivalent **scan + policy** check, not an end-to-end Hub installation
or a model-scored evaluation run. It does not verify Hub download/update behavior,
loading in an agent, other scanner versions, or other installers. Do not disable
security checks if another installer reports findings; inspect them normally.
