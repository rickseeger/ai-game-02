# Prebuilt artifacts — City Walkthrough (ai-game-02)

These are self-contained standalone builds. No Python or other dependencies are
required on the target machine.

| File | Platform | Size | What it is |
|------|----------|------|------------|
| `citywalk-linux-x86_64`        | Linux x86-64 (glibc)  | ~12 MB | one-file executable |
| `citywalk-windows-x86_64.exe`  | Windows x86-64        | ~7 MB  | one-file console executable |

Both are built from the same `run.py` + `citywalk/` source by PyInstaller
`--onefile` (see `citywalk.spec` in the repo root). They bundle a CPython 3.12
interpreter and the full standard library, so they run anywhere the matching OS
runs a console program.

## Linux

    chmod +x citywalk-linux-x86_64
    ./citywalk-linux-x86_64                  # interactive walk
    ./citywalk-linux-x86_64 --snapshot       # one frame, plain text (headless)
    ./citywalk-linux-x86_64 --demo           # scripted fly-through -> citywalk_demo.ans

## Windows

Double-click `citywalk-windows-x86_64.exe` (a console app). Windows Terminal is
recommended (truecolor); legacy conhost works at 256-color. On first run Windows
SmartScreen may warn because the exe is unsigned — choose "More info" -> "Run
anyway".

From a command prompt you can also run the headless modes:

    citywalk-windows-x86_64.exe --snapshot
    citywalk-windows-x86_64.exe --demo

## Verification

SHA-256 checksums are in `SHA256SUMS.txt`. Verify a download with:

    sha256sum -c SHA256SUMS.txt        # Linux
    certutil -hashfile citywalk-windows-x86_64.exe SHA256   # Windows
