# Troubleshooting

These steps apply to Quilchoom's current CLI. If you are working from a source
checkout, prefix commands with `uv run` (for example, `uv run quilchoom --help`).

## Not inside a Git repository

**Problem:** `quilchoom init` reports `Not inside a Git repository.`

**Possible cause:** Your terminal is outside the Git repository you want to track.

**Resolution:** Change into that repository, then initialize Quilchoom:

```bash
cd /path/to/your/repository
git rev-parse --show-toplevel
quilchoom init
```

The path is a placeholder. If `git rev-parse` fails, first locate your existing
repository. Only use `git init` if you intend to create a new Git repository;
`quilchoom init` does not create one for you.

## Quilchoom is not initialized

**Problem:** A project command reports
`Quilchoom is not initialized in this repository.`

**Possible cause:** This repository does not have a Quilchoom workspace yet.
Initializing one repository does not initialize other repositories.

**Resolution:** Run these commands from the repository you want to track:

```bash
quilchoom init
quilchoom status
quilchoom capture
```

Initialization creates the local `.quilchoom/` workspace. `status` helps you see
the next workflow step; initialization alone does not capture commits or generate
knowledge. Do not delete an existing workspace as a troubleshooting shortcut:
it contains your project state and generated document history.

## Missing API key

**Problem:** An AI-backed command reports `Unable to configure AI.` and mentions
that `OPENAI_API_KEY` is missing or empty.

**Possible cause:** The environment of the terminal running Quilchoom has no
non-empty key. Git capture and status do not require an AI key, and `distill`
can finish without one when there is no pending evidence.

**Resolution:** Set your own key in the same terminal, then retry the failed
command. The value below is a placeholder, not a working key.

Linux / macOS:

```bash
export OPENAI_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

Do not put the key in `.quilchoom/config.toml`, commit it, or paste it into an
issue. See [API credentials](../README.md#api-credentials).

## Credentials are rejected

**Problem:** An AI-backed command reports `AI authentication failed.` with
`OpenAI rejected the configured credentials.`

**Possible cause:** A key is present, but the provider rejects it; for example,
it may be incorrect or revoked. Setting a non-empty value is not proof that
it is valid.

**Resolution:** Verify your key with your provider and set the correct value in
the terminal running Quilchoom, as shown above. Then retry the failed command.
Reinitializing the project will not repair provider credentials.

## Provider connection or rate-limit failure

**Problem:** An AI-backed command reports
`AI provider is temporarily unavailable.` The explanation may say
`Could not connect to OpenAI.` or
`OpenAI temporarily rate-limited the request.`

**Possible cause:** A connectivity failure or provider rate limit prevented the
request from completing. These are distinct from authentication failures.

**Resolution:** For connection failures, check your network connection and any
proxy restrictions. For rate limits, wait before retrying and check your
provider's usage limits. Quilchoom already retries these transient failures up
to three total attempts, so repeatedly rerunning immediately may not help.
Once the cause is resolved, retry the failed command rather than deleting the
workspace or recapturing the same history. AI requests use your provider
credentials and may incur costs.

## Finding a command or option

**Problem:** You are unsure which command to run, or the CLI rejects an option.

**Possible cause:** Options belong to different command levels; global options
and nested command options are not interchangeable.

**Resolution:** Consult help at the relevant level:

```bash
quilchoom --help
quilchoom log --help
quilchoom scribe --help
quilchoom scribe export --help
```

For example, document export takes a document target and destination:
`quilchoom scribe export readme README.md`. Check help before using overwrite
options on an existing file.

## Investigating an error with debug mode

**Problem:** The normal concise error does not provide enough detail to diagnose
an unexpected failure, or placing `--debug` after a command is rejected.

**Possible cause:** Expected errors normally have a short explanation and next
step. `--debug` is a global option, so it must appear before the command.

**Resolution:** Retry the failing command with debug mode at the correct level:

```bash
quilchoom --debug distill
quilchoom --debug scribe generate readme
```

Debug mode exposes the underlying exception and traceback. It does not fix the
cause, and retrying an AI command can make another provider request. Before
sharing any output, review and redact credentials and private repository data.
For a bug report, include `quilchoom --version`, `python --version`, your OS,
the command, expected and actual behavior, and minimal reproduction steps.
