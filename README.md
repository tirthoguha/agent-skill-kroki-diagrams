# Kroki diagrams for Claude Code and OpenAI Codex

A shared skill for [Claude Code](https://claude.com/claude-code) and
[OpenAI Codex](https://developers.openai.com/codex/) that renders Mermaid (and
other [Kroki](https://kroki.io)-supported) diagrams to **white-background PNG or SVG files** suitable for Confluence / Slack / docs, then reviews each render visually
for readability before declaring it done.

The shared workflow grounds diagrams in source material, keeps complex views
focused, and reviews both factual accuracy and visual readability. It prefers
lossless image flattening and checks render failures before processing output.

The skill drives a **local** Kroki stack: the main `kroki` engine plus its
`kroki-mermaid` companion, wired together on a shared Docker network.

## Sample gallery

Explore the [architecture, sequence, and state examples](examples/report-export/README.md),
each with PNG, SVG, and editable Mermaid source. For an interactive format
comparison, open `examples/report-export/index.html` locally after cloning.

![Example report-export architecture](examples/report-export/01-architecture.png)

## Architecture

```
Claude Code / Codex ──curl──▶ kroki  (localhost:8585)
                               │  delegates Mermaid rendering
                               ▼  via KROKI_MERMAID_HOST over kroki-net
                            kroki-mermaid  (internal, :8002)
```

Docker Compose uses the project name `agent-skill-kroki-diagrams`, even when
the checkout folder has a different name. The service/container names remain
`kroki` and `kroki-mermaid`.

Only `kroki` publishes a port. It defaults to **8585** (port 8000 is commonly
busy) and is overridable via `KROKI_PORT`. The companion is reachable only on the
internal `kroki-net` bridge network, by DNS hostname `kroki-mermaid`.

## Prerequisites

- **Docker** with Compose v2 (Docker Desktop on macOS/Windows, or Docker Engine
  + `docker compose` plugin on Linux)
- **Python 3** for the bundled Mermaid renderer
- **`curl`** (preinstalled on macOS/Linux; on Windows use Git Bash, WSL, or the
  bundled `curl.exe`)
- **An image flattener** for the alpha-strip step — the skill auto-detects, in
  order of preference:
  | Tool | Platforms | Install |
  |---|---|---|
  | **ImageMagick** (`magick`/`convert`) | macOS, Linux, Windows | `brew install imagemagick` · `apt install imagemagick` · `choco install imagemagick` |
  | **Pillow** (`python3` + PIL) | any | `pip install pillow` |
  | **`sips`** | macOS only | built in; JPEG fallback can soften text |

  On Linux/Windows there is no `sips`, so install **ImageMagick** (recommended) or
  Pillow.

### Python setup

The bundled renderer requires **Python 3.9 or newer** and the `curl` executable.
SVG rendering uses only Python's standard library. For lossless PNG conversion
without ImageMagick, install Pillow using the optional requirements file:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If you already have ImageMagick, no Python packages are required. The macOS
`sips` fallback also works without packages, but its JPEG intermediate can soften
text. Run the renderer with the Python environment where you installed Pillow.

## Install

**Step 1 — start the Kroki stack** (both containers, shared network):

```bash
git clone https://github.com/tirthoguha/agent-skill-kroki-diagrams.git
cd agent-skill-kroki-diagrams
docker compose up -d                          # or: KROKI_PORT=9123 docker compose up -d
curl -sf http://localhost:8585/ >/dev/null && echo "Kroki OK"
```

**Step 2 — install the skill for your agent.** Both agents use the same
`skills/kroki/SKILL.md`; choose either or both installations below.

### Claude Code

A skill is just a directory
containing a `SKILL.md`; Claude discovers it under `~/.claude/skills/` (personal)
or `.claude/skills/` (this project only). The directory name becomes the command,
so installing it as `kroki` gives you **`/kroki`**. Symlink it so it tracks
`git pull`s:

```bash
# Personal (all your projects), from this repo root:
mkdir -p "$HOME/.claude/skills"
ln -s "$PWD/skills/kroki" ~/.claude/skills/kroki
# …or project-scoped within this repo (relative link works for teammates):
mkdir -p .claude/skills
ln -s ../../skills/kroki .claude/skills/kroki
```

> **Windows:** use `mklink /D` (cmd, admin) or `New-Item -ItemType SymbolicLink`
> (PowerShell), or just copy the folder: `cp -r skills/kroki ~/.claude/skills/`.

Then in Claude Code ask for any diagram ("draw the architecture", "sequence
diagram of the auth flow", …) — or type `/kroki` — and the skill takes over. It
still needs the Kroki stack from **Step 1** running locally.

### OpenAI Codex

From this repo root, install a personal skill:

```bash
mkdir -p "$HOME/.agents/skills"
ln -s "$PWD/skills/kroki" "$HOME/.agents/skills/kroki"
```

Or install only for this repository using a relative symlink that teammates can
use after checking it in:

```bash
mkdir -p .agents/skills
ln -s ../../skills/kroki .agents/skills/kroki
```

Choose one scope to avoid duplicate entries. These commands expect no existing
`kroki` entry at the destination; inspect an existing installation before replacing
it. On Windows, use the symlink commands above via a supported shell, or copy
`skills/kroki` into the chosen skills directory instead. Copies need to be updated
after pulling changes.

In Codex CLI or the IDE extension, select the skill with `/skills` or mention it:

```text
$kroki Create an engineering sequence diagram of login:
browser -> API -> identity provider -> API -> browser.
Put the source and PNG in ./docs/diagrams.
```

Codex can also select the skill automatically when a request matches its
description. Restart Codex if it does not discover the new installation.
See the [official skills documentation](https://developers.openai.com/codex/skills).

### Execution environment

Use a local agent session with access to Docker, `curl`, an image flattener, and
an image-viewing tool for visual review. In a remote/cloud session, `localhost`
refers to that remote environment, not your laptop; it needs its own reachable
Kroki stack. Installing the skill alone does not start or provision Docker.

Respect the agent host's filesystem and network permissions. The default output
folder may be outside a Codex workspace; set `KROKI_DIAGRAMS_DIR` to a permitted
location or explicitly request a workspace output folder as in the example above.
The skill reports when visual review is unavailable instead of claiming it passed.

## Configuring the port

The stack and the skill both read `KROKI_PORT` (default `8585`). Export it once
in your shell so `docker compose` and your agent agree:

```bash
export KROKI_PORT=9123   # add to ~/.zshrc / ~/.bashrc to persist
```

## Configuring the output directory

By default the skill writes `.mmd` sources and rendered PNG/SVG files to
`~/Documents/kroki-diagrams/<topic-slug>/`. Override the base directory by
exporting `KROKI_DIAGRAMS_DIR` (the skill reads it via the shell):

```bash
export KROKI_DIAGRAMS_DIR="$HOME/diagrams"   # add to ~/.zshrc / ~/.bashrc to persist
```

You can also override per request by telling the agent explicitly ("put these in
`./docs/diagrams`") — an explicit instruction wins over both the env var and the
default.

## Why a compose file instead of two `docker run`s

Kroki's Mermaid support lives in a separate `kroki-mermaid` container that the
main engine calls over the network. Running that by hand means two ordered
`docker run`s plus a manually created network. The compose file encodes the whole
topology declaratively so it comes up with one command:

- both containers on a shared `kroki-net` bridge network,
- `kroki` finds the companion by DNS via `KROKI_MERMAID_HOST=kroki-mermaid`,
- `restart: unless-stopped` so the stack survives reboots,
- the host port is parameterised (`KROKI_PORT`, default `8585`).

## Generated diagrams and examples

Normal task outputs stay outside the repository by default, under
`KROKI_DIAGRAMS_DIR` or `~/Documents/kroki-diagrams/<topic>/`. They are not
committed unless requested. The curated [sample gallery](examples/report-export/)
is an intentional exception: its Mermaid sources, PNGs, and SVGs demonstrate the
skill and can be regenerated.

## How this repo is packaged

```
agent-skill-kroki-diagrams/
├── skills/
│   └── kroki/
│       ├── SKILL.md        # shared instructions for both agents
│       ├── agents/
│       │   └── openai.yaml # Codex display metadata
│       └── scripts/
│           └── render.py   # validated Mermaid PNG/SVG output
├── examples/report-export/ # sample gallery, sources, PNGs and SVGs
├── tests/                  # local renderer regression tests
├── requirements.txt        # optional Pillow dependency for lossless PNG
├── docker-compose.yml      # the local Kroki stack the skill drives
├── LICENSE
└── README.md
```

It ships as a **bare skill** with one shared source. Codex discovers it under
`~/.agents/skills/` or `.agents/skills/` and supports `$kroki` invocation in the
CLI/IDE. Claude Code loads any `<name>/SKILL.md` placed under
`~/.claude/skills/` (personal) or `.claude/skills/` (project), and the directory
name is the command. Installed as `kroki`, that's `/kroki` — no namespace prefix.

> **Want it as a plugin instead?** Claude Code can also distribute skills as
> plugins via a marketplace (`/plugin marketplace add <owner/repo>` →
> `/plugin install …`). That route namespaces the command as `/<plugin>:<skill>`,
> which is why this repo skips it — a bare skill keeps the command a clean
> `/kroki`. To wrap it as a plugin anyway, add a `.claude-plugin/plugin.json`
> (`name`, `description`, `version`, `author`) at the repo root plus a
> `.claude-plugin/marketplace.json` listing it with `source: "."`.

## License / attribution

This repo (the skill, compose stack, and tooling) is MIT-licensed — see
[LICENSE](LICENSE). `yuzutech/kroki` and `yuzutech/kroki-mermaid` are third-party
images ([kroki.io](https://kroki.io), also MIT) and are not redistributed here —
the compose file just pulls them.

## Output choices and rendering

The skill chooses PNG for sharing, SVG for scaling, and both only when needed.
It keeps editable Mermaid source and reviews SVG separately in a browser.
The Mermaid helper requires Python 3 and curl; PNG conversion additionally uses
ImageMagick, Pillow, or the macOS sips fallback.

```bash
python3 skills/kroki/scripts/render.py /path/to/diagram.mmd --format both
```

The skill resolves the destination from an explicit user request, then
`KROKI_DIAGRAMS_DIR`, then `~/Documents/kroki-diagrams/<topic>/`, and writes the
source there. The standalone helper writes outputs beside that source
(`--out-dir` overrides this); it does not separately resolve `KROKI_DIAGRAMS_DIR`. The helper
reads `KROKI_PORT` or accepts `--port`. It validates all requested formats before
replacing previous outputs, and applies opaque white backgrounds to PNG and SVG.

## Tests

The regression tests use a local HTTP fixture, so Docker is not required. Python
needs one of the PNG flatteners listed above for the two-format failure test.

```bash
python3 -m unittest discover -s tests -v
```
