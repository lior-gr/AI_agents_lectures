# AI Agents Lectures

## Git LFS Requirement for Media Files

This repository tracks `*.mp4` and `*.wav` using Git LFS.

### One-time setup

```bash
git lfs install
```

### If videos/audio appear as tiny text pointer files

Run:

```bash
git lfs pull
git lfs checkout
```

### Automatic media download on `git pull`

- Keep LFS smudge enabled (default after `git lfs install`).
- Do not set `GIT_LFS_SKIP_SMUDGE=1`.

### Quick verification

```bash
git lfs ls-files
```
