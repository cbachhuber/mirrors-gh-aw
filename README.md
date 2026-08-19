# mirrors-gh-aw

A [prek](https://github.com/j178/prek)/[pre-commit](https://pre-commit.com) mirror for the [gh-aw](https://github.com/github/gh-aw) agentic-workflow compiler.

It lets you run `gh aw compile` as a pre-commit hook **without installing `gh` or the `gh-aw` extension on the machine**.
`gh-aw` ships only as a `gh` CLI extension and as raw per-platform release binaries; it can't be `go install`ed (its `go.mod` uses `replace` directives) and has no PyPI wheel, so none of pre-commit's tool-managing languages can fetch it directly.
This mirror wraps the released binary in a tiny `language: python` package that downloads it on first run, verifies it against the committed `checksums.txt`, caches it, and execs it.

## Usage

Add to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/cbachhuber/mirrors-gh-aw
  rev: v0.86.2 # keep in sync with the gh-aw compiler_version in your .lock.yml files
  hooks:
    - id: gh-aw-compile
```

The `gh-aw-compile` hook recompiles any changed `.github/workflows/*.md` and lets pre-commit fail the commit when the regenerated `.lock.yml` differs from what you staged.

A generic `gh-aw` hook is also provided for running arbitrary subcommands via `args`.

## Version pinning

`rev` must match the `gh-aw` version that produced your committed `.lock.yml` files (the `compiler_version` in each lock's `# gh-aw-metadata:` header).
The mirror's package version, git tag, and `checksums.txt` all track one gh-aw release.

## Auto-updates

`.github/workflows/mirror.yml` runs `update.py` on a schedule: when a newer gh-aw release exists it refreshes `__version__` and `checksums.txt`, then commits and pushes a matching `vX.Y.Z` tag.
Consumers move forward by bumping `rev` (e.g. via `pre-commit autoupdate`).

## Supported platforms

Linux, macOS, and Windows on amd64/arm64 (plus 386 where gh-aw publishes it), matching the gh-aw release assets.
