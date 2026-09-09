---
name: kroki
description: Create architecture, sequence, and state diagrams as PNG or SVG using local Kroki. Use for shareable diagram files and visual review; use inline Mermaid for small conversational explanations.
---

# kroki

Render Mermaid (and other Kroki-supported) diagrams as PNG or SVG using the user's **local** Kroki Docker container, then **open the rendered output and review it visually** for readability before declaring the job done.

This shared skill works with Claude Code and OpenAI Codex. Use the host's shell
and image-viewing tools; tool names vary by agent. A local session must be able
to reach the Kroki stack. In remote sessions, `localhost` is the remote machine.

## When to use

- User asks for "a diagram", "architecture diagram", "flow diagram", "sequence diagram", "state machine", "lifecycle diagram", or similar.
- User asks for diagrams to put in docs / Confluence / a PR description.
- User says "render this mermaid" or "make a picture of this flow".

Do NOT use for: small inline diagrams that would fit in a code block (just use a fenced ```mermaid block). Use this skill when an image file is the actual deliverable.

## Prerequisites (verify before generating)

The user runs Kroki locally. The published port defaults to **8585** but is
overridable via the `KROKI_PORT` environment variable — resolve it through the
shell so the variable wins, and reuse `$PORT` everywhere below:

```bash
PORT="${KROKI_PORT:-8585}"
docker ps --filter "name=kroki" --format "{{.Names}}\t{{.Ports}}" \
  && curl -sf "http://localhost:$PORT/" > /dev/null && echo "Kroki OK" || echo "Kroki NOT REACHABLE"
```

If the container isn't running or the port doesn't respond, **stop** and tell the user:

> Kroki isn't reachable on `localhost:$PORT`. Start it with the bundled compose
> stack (recommended):
> ```bash
> docker compose up -d          # from the skill's repo dir
> ```
> …or manually on a shared network:
> ```bash
> docker network create kroki-net
> docker run -d --name kroki-mermaid --network kroki-net yuzutech/kroki-mermaid
> docker run -d --name kroki --network kroki-net \
>   -e KROKI_MERMAID_HOST=kroki-mermaid -p "${KROKI_PORT:-8585}:8000" yuzutech/kroki
> ```

Do not attempt to render until they confirm it's up.

## Scope and output choice

Use the conversation to infer the subject, audience, and scope. For an explicitly
requested sample, choose a small fictional example and label it as such. Ask one
consolidated question only when missing facts would materially change the diagram.

| Need | Output |
|---|---|
| Short explanation in a chat that renders Mermaid | Inline Mermaid; no server needed |
| Copy into docs, chat, or a destination with unknown SVG support | Opaque white PNG plus editable source |
| Zooming, resizing, or vector-friendly documentation | SVG plus editable source |
| Both easy sharing and scalable reuse, or explicit comparison | PNG and SVG plus one shared source |

Default to PNG for unspecified image requests. Do not generate every format by
default. Preserve the `.mmd` source; SVG is scalable output, not a replacement for
semantic source editing. SVG support varies by destination, especially for HTML
labels. Prefer native SVG text (`flowchart: {htmlLabels: false}`) for portable
flowchart exports, and verify the actual SVG in a browser. Interactivity requires
a separate interactive artifact; an SVG alone is not an interactive application.

## Diagram design

- Start with the reader's question. Use one overview or several focused diagrams
  when a single canvas would mix unrelated concerns or become hard to read.
- Ground participants, boundaries, and arrow directions in the supplied code or
  documentation. Label assumptions; do not invent services or failure paths.
- Use short, meaningful labels. Explain unfamiliar abbreviations and give colors
  a consistent meaning; include a legend when their meaning is not obvious.
- Show the relevant system boundary and distinguish synchronous calls, asynchronous
  work, and responses. Include error paths only when they matter to the requested scope.
- Match the output to the request: use an inline Mermaid block for a small inline
  diagram, and this rendering workflow when the deliverable is an image file.

### Layout for the destination

- Start with a single reading direction. Prefer top-to-bottom for narrow chat or
  document columns and left-to-right for genuinely horizontal comparisons.
- Inspect at the intended display width (roughly 700–900 px for a document), not
  only zoomed in. If labels become tiny, shorten or split the diagram before
  increasing image resolution. Do not enlarge a small raster and call it sharper.
- Architecture: group only meaningful boundaries, keep similar components at the
  same level, and label edges with relationships rather than vague verbs.
- Sequence: order participants by interaction, use solid calls and dashed replies,
  and label background phases explicitly. A queued request being accepted is not
  the same as its background work completing.
- State: name states as conditions (Queued, Running, Ready); label transitions
  with events or guards. Distinguish failure, retry, and terminal outcomes only
  when the example or source establishes them.
- Use restrained role-based colors and explicit text labels, so the meaning
  survives grayscale. A boundary title must not intersect an incoming arrow.

## Workflow

For each diagram requested:

1. **Decide the diagram type** based on the request (after asking if needed):
   - System or architecture overview → `flowchart LR` or `flowchart TB`
   - Step-by-step interaction (caller → service → external system) → `sequenceDiagram`
   - States and transitions of an entity → `stateDiagram-v2`
   - Dependency graph → `graph LR`
   - ERD → `erDiagram`
   - Git branching → `gitGraph`
   - Class hierarchy → `classDiagram`

2. **Write the `.mmd` source** to a **local-only** directory — diagrams are scratch artefacts intended for Confluence / Slack / docs, not committed to project repos.

   **Resolve the output base directory** from the `KROKI_DIAGRAMS_DIR`
   environment variable, falling back to `~/Documents/kroki-diagrams` when unset.
   Always expand it through the shell so the variable wins:

   ```bash
   BASE="${KROKI_DIAGRAMS_DIR:-$HOME/Documents/kroki-diagrams}"
   ```

   The full path for each source file is then:

   ```
   $BASE/<feature-or-topic-slug>/NN-<descriptive-name>.mmd
   ```

   Respect the host's filesystem permissions. If this directory is not writable,
   use an explicitly supplied writable output location or request the required
   permission; do not silently change the destination.

   Create the directory if it doesn't exist. The slug is short kebab-case (e.g., `custom-domain`, `billing-flow`, `auth-handshake`). NN is a zero-padded 2-digit ordinal (`01`, `02`, …).

   A user can also override the location for a single request by saying so
   explicitly ("put them in ./docs/diagrams") — an explicit instruction beats
   both the env var and the default. Never put diagrams under the current project
   repo unless told to — the default assumption is the user takes them to
   Confluence and doesn't want them tracked in git.

3. **Render the selected formats** using the bundled helper. Resolve its path
   relative to this skill directory, not the current project. It needs Python 3.9 or newer
   and `curl`; PNG additionally needs ImageMagick, Pillow, or macOS `sips`.

   ```bash
   python3 "<skill-dir>/scripts/render.py" "<path>.mmd" --format png
   # Choose svg or both only when the requested use calls for it:
   python3 "<skill-dir>/scripts/render.py" "<path>.mmd" --format both
   ```

   The helper reads `KROKI_PORT` (default 8585); `--port` overrides it. Outputs
   go alongside the source unless `--out-dir` is supplied. It checks HTTP failures,
   validates output, and stages all requested formats before replacing prior
   outputs. A failed render must not be delivered as a successful revision.

4. **Check the format.** The helper flattens PNG to opaque RGB, preferring
   lossless conversion, and inserts a white canvas rectangle covering the SVG
   viewBox. It preserves SVG text and shapes. SVG needs no raster flattener.
   Do not send SVG through JPEG or PNG conversion for the deliverable. For other
   Kroki engines, verify the engine's supported formats first; this helper is
   intentionally Mermaid-only.

5. **Visually review each selected output** using the host's available image-viewing tool (for example, Claude Code's `Read` or Codex's `view_image`, when available). A shell command that only reports file metadata does not count as visual review. For SVG, open the actual SVG in a browser and inspect it or a browser screenshot; reviewing the separately generated PNG does not prove the SVG looks correct. If image viewing is unavailable, report that visual review could not be completed and do not claim it passed. Otherwise, check the criteria in the next section and either:
   - Declare it acceptable, or
   - Edit the `.mmd` source and re-render (+ re-flatten) until it passes.

6. **Report results** to the user with a 1–2 line description of each diagram + the path. Do NOT embed the diagrams inside `.md` files unless the user explicitly asks — they may be heading to Confluence and want only the file references.

## Review criteria (the vision pass)

After opening each selected output (SVG in a browser), check:

| Issue | Symptom | Fix |
|---|---|---|
| **Special chars in guards** | A bracket guard like `[CNAME wrong ✗]` renders as `[CNAME wrong [?]]` because Mermaid mis-parses unicode inside `alt`/`else` labels | Strip ✓/✗/emoji from guards; use plain text. Move the glyph into a `Note over` if needed. |
| **Too many lifelines** | Sequence diagram is wider than 1800 px or has 7+ participants | Split into multiple diagrams (`03a-…`, `03b-…`), or merge near-duplicate lifelines (e.g., "Customer" + "Customer's DNS" can become just "Customer" with a `Note`). |
| **Snaking arrows** | Flow lines cross over themselves or zigzag because nodes are placed awkwardly | Switch direction (`flowchart LR` ↔ `flowchart TB`) or move related nodes into a `subgraph` to constrain layout. |
| **Floating notes overlap** | `note right of X` produces a dashed connector that crosses real arrows | Drop redundant notes, or place them at the diagram edges (use `note left of` to push them outward). |
| **Tiny illegible text** | Diagram is wider than 2000 px and labels look pixelated when scaled down | Shorten participant names, abbreviate. Long technical names like `Background pool (customdomain-teardown)` → `Async pool` + a `Note over` with the long form. |
| **Font fallback** | Diagram uses default Mermaid font even though the source asked for Open Sans / Inter / etc. | The Kroki Mermaid container doesn't have custom fonts installed. Don't try to fight it — remove the `fontFamily` from `%%{init: …}%%` so the default doesn't generate a "missing font" warning. |
| **Transparent background** | PNG looks fine in your reader but has alpha — labels become unreadable on dark Confluence / Slack | `?bgColor=white` does not guarantee an RGB output. Use the helper's opaque white output. Verify with `file <path>.png` → should say `8-bit/color RGB`, not `RGBA`. |
| **Logical errors** | Arrows don't match the actual code/flow, missing async vs sync distinction, etc. | Re-read the source code / docs the diagram represents, fix factual errors. |

If a fix requires re-rendering, **edit the `.mmd` and re-run the renderer** — don't try to surgically patch the PNG.

## Standard init block

Start every Mermaid file with this header. No `fontFamily`, no theme variables that depend on installed fonts:

```mermaid
%%{init: {'theme':'default'}}%%
```

If the user wants a specific theme (forest, dark, base), add it — but don't add font hints. Theme variables for colors work fine; font ones don't unless they bake the font into the container.

## Useful color conventions

When using `classDef` for node coloring, these palettes look fine on white background and remain legible when shrunk:

| Role | Fill | Stroke |
|---|---|---|
| Edge / network function | `#e8f5f8` | `#5eadc6` |
| Data store / DB / cache | `#fff7e0` | `#d4a017` |
| External system / customer | `#f0f4ff` | `#3b5bdb` |
| Internal service | `#f3e8f8` | `#8b5cf6` |
| Async / background work | `#fff5d6` (in `rect rgb(…)` for sequence shading) | — |
| Synchronous / immediate | `#e8f5f8` (in `rect rgb(…)`) | — |

## Sequence diagram tip — rect for sync vs async

When a sequence has a synchronous prefix and an async tail (a common pattern), wrap each in a `rect rgb(…)` block with a `Note over` heading:

```
rect rgb(232, 245, 248)
Note over Svc: Synchronous (~2s)
… steps …
end

rect rgb(255, 245, 220)
Note over Pool: Async (1–10 min)
… steps …
end
```

This makes the phase boundary unmissable.

## Common Kroki gotchas

- **Invalid or large Mermaid sources** can return HTTP 400 — use `curl --fail`, check its exit status, and inspect the renderer response before retrying.
- **POST body** must be UTF-8 — avoid stray BOMs or CRLF (some editors add them).
- **Render times** for big sequences can be 3–6 seconds — that's normal; not stuck.
- **SVG background**: do not rely on the PNG `bgColor` query for vector exports. The helper inserts an explicit white background rectangle.
- **Check PNG alpha** even with `?bgColor=white`. Renderer output may retain an alpha channel or transparent regions. Always flatten to RGB before delivering (see step 4) — otherwise the diagram is unreadable on dark themes.

## Final report format

When done, summarize as below. Only claim visual review if you actually inspected
every image; otherwise identify which images were not reviewed and why:

```
Generated N diagrams under $BASE/<slug>/:
  01-architecture.png         — <one-line description>
  02-state-machine.png        — <one-line description>
  …
All delivered images have white backgrounds and have been visually reviewed; specific tweaks made: <list>.
```

Don't list every byte count, dimension, or HTTP code in the final report — those are debugging output, not deliverables.

Reminder: do NOT embed these PNGs into project markdown files unless the user explicitly asks. The default assumption is that the user will copy them into Confluence or another external doc system.
