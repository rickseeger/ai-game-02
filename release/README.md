# Prebuilt artifacts — citywalk2d (ai-game-02)

Self-contained standalone builds. No Python or any other dependency is
required on the target machine — each file bundles a CPython 3.12
interpreter and the full standard library.

| File | Platform | Size | What it is |
|------|----------|------|------------|
| `citywalk2d-linux-x86_64`       | Linux x86-64 (glibc) | ~11.4 MB | one-file console executable |
| `citywalk2d-windows-x86_64.exe` | Windows x86-64       | ~7.1 MB  | one-file console executable |

Both are built from the same `run.py` + `citywalk2d/` source by PyInstaller
`--onefile` (see `citywalk2d.spec` in the repo root). They bundle CPython 3.12
and the full standard library, so they run anywhere the matching OS runs a
console program.

## Linux

```sh
chmod +x citywalk2d-linux-x86_64
./citywalk2d-linux-x86_64                          # interactive walk
./citywalk2d-linux-x86_64 --demo --no-color        # one static city render
./citywalk2d-linux-x86_64 --script walk.txt --no-color   # scripted, headless
```

Controls (interactive): WASD / arrow keys to move, `q` / `Esc` / Ctrl-C to quit.

## Windows

Double-click `citywalk2d-windows-x86_64.exe` (a console app). Windows Terminal
is recommended (truecolor); legacy conhost works at 256-color. On first run
Windows SmartScreen may warn because the exe is unsigned — choose
"More info" → "Run anyway".

From a command prompt you can also run the headless modes:

```bat
citywalk2d-windows-x86_64.exe --demo --no-color
citywalk2d-windows-x86_64.exe --script walk.txt --no-color
```

## Verification

SHA-256 checksums are in `SHA256SUMS.txt`. Verify a download with:

```sh
sha256sum -c SHA256SUMS.txt                                  # Linux
certutil -hashfile citywalk2d-windows-x86_64.exe SHA256      # Windows
```

The binaries are reproducible from source — `citywalk2d.spec` at the repo root
plus the `package` jobs in `.github/workflows/ci.yml` rebuild both artifacts
cleanly on ubuntu-latest and windows-latest.
