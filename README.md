# Windows push-to-talk helper

Version: **0.2.4-beta.1** (Windows/game compatibility pending).

Run on the Windows 10/11 gaming PC, not the Linux soundboard server.
Install Python 3 with Tkinter, then run:

```powershell
py soundboard-ptt.py
```

On the main soundboard enable Remote control or refresh its pairing code.
Enter its HTTPS address and pairing code in the helper. Click Pair and connect.
Enter your Squad and Local keys (J and K by default), then choose Squad, Local, or Off. Single letters, digits, F1–F24, and named keys are supported; key combinations are not. Local sounds, TTS, and history replays
on that paired browser hold the selected key. Remote-triggered Local audio is
included. Discord bot playback does not press a key.

Keep the main soundboard and helper running. Disconnect releases the key.
The helper emits Windows scan-code events to the currently focused app:
keep Wardogs focused when triggering sounds. Game input acceptance must be
tested on Windows; some games block synthetic input. If the game runs elevated,
the helper may require matching privileges. It does not bypass game protections.

Audio onset is detected through polling, so a very short clip may finish before
PTT engages and the start of a clip may be clipped. A connection error releases
the key after the request timeout (up to four seconds across two requests).
This first version pairs again when the helper is restarted.

## Build a standalone Windows EXE

Install Python 3 on Windows, then double-click `build-exe.bat`. It creates
`dist/Giro-Soundboard-PTT-v<version>.exe`. The finished EXE does not require Python.
The Windows build and game input still need testing on your PC.

## Automatic GitHub releases

GitHub Actions builds the EXE on Windows and uploads it with a SHA256 checksum.
No extra account token is needed; the workflow uses GitHub's repository token.

To publish the current version from a checkout:

```bash
git tag v0.2.4-beta.1
git push origin v0.2.4-beta.1
```

Alternatively, create and publish a release on GitHub with that tag, targeting
main. Watch the Build Windows Helper Release workflow in the Actions tab;
the EXE appears under the release's Assets when the build succeeds.
Tags must match VERSION and the Python script's __version__.

Beta versions are prereleases. Their direct EXE download URL is:
https://github.com/thauch/giro-soundboard-ptt/releases/download/v0.2.4-beta.1/Giro-Soundboard-PTT-v0.2.4-beta.1.exe

EXE filenames include their release version. Update download links for each release.
