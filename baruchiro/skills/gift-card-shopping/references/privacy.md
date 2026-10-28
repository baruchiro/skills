# Privacy and external state

Keep wallet, config, operational catalog and cache outside the skill package and every Git checkout. Synthetic examples are the only tracked JSON inventory fixtures. No PIN, barcode, card number, credential or personal redemption URL belongs in any input. Local IDs are invented identifiers, never card numbers.

Obtain consent before reading exact private files. Hide balance amounts unless explicitly requested in this conversation. Holdings, labels and inferred balance states are still personal information; any output the agent reads may reach its history/model provider. Local execution is not a privacy sandbox.

The helper has no network fetches, subprocess execution or input/cache writes. `urllib.parse` is used only for URL syntax checks. It does not enforce filesystem permissions, encrypt data or prevent backups/cloud synchronization. A private POSIX directory with mode 0700 and files 0600 is recommended; other platforms require their own policy.

## Current implementation limitations

Do not claim complete secret/schema protection. Unknown-field rejection currently covers top-level objects/config, not every nested object; a forbidden extra field can therefore be ignored. File/JSON/IO error messages can contain full paths or other input details. Config itself and package boundaries are not fully enforced. See limits before supplying real data. Manually inspect every input and do not copy error output into a public issue/PR.

The command-line engine reads files supplied by the user; this package never discovers accounts or automatically loads a real wallet. Permission to research public sources is not permission to read, update or publish private state.
