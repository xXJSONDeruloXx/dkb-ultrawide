# Donkey Kong Bananza ultrawide for Lichii

**Experimental. Genuine horizontal view expansion is verified at 3440x1440 in Ingot Isle.
HUDs and other 2D layouts still stretch.**

This is a small ExeFS IPS32 patch, plus a Python generator for custom aspect ratios.
It changes the horizontal perspective of cameras using the game's original 16:9
aspect. It preserves vertical field of view and also updates the aspect field read
by the camera's frustum calculations. Other camera aspects are left alone.

## Supported build

- Title ID: `040074A01BF12000`
- Main NSO build ID: `E25C90C1C136638885659FD55BF8A03B3403489D000000000000000000000000`
- Tested loader: Lichii build 70, `286117c7e0-nx2`, Windows PGO.
- The local NUP filename labels the game v3.2.0; compatibility is determined by
  the executable build ID, not that filename. The container update's version
  integer is `0x70000`.

No game data, firmware, keys, or saves are distributed here. The original NUP is
read only. A different game update requires analysis of its executable.

## Use the generated patch

The patch in `dist/040074A01BF12000/DKB Ultrawide` targets **3440×1440 (43:18)**.
Copy that `DKB Ultrawide` folder to:

```text
%APPDATA%\eden\load\040074A01BF12000\
```

Alternatively, right-click the game in Lichii and open its mod data location.
Enable only one aspect patch at a time, then restart the game. Set the game's
Graphics → Aspect Ratio to **Stretch** and use fullscreen at the matching display
ratio. A differently shaped window will distort the result. Lichii's `21:9`
display option is a nominal 7:3, which differs from both 3440×1440 and 2560×1080.

To undo, disable `DKB Ultrawide` in the game's add-ons and restore Aspect Ratio
to `16:9`. Restart the game.

## Generate another ratio

Python 3.10 or later:

```powershell
python -m pip install -r requirements.txt
python dkb_ultrawide.py --game "D:\path\game.nup" --ratio 21:9 --output presets/21x9
python dkb_ultrawide.py --game "D:\path\game.nup" --ratio 2560:1080 --output presets/2560x1080
python dkb_ultrawide.py --game "D:\path\game.nup" --ratio 32:9 --output presets/32x9
```

Add `--install` to copy the generated patch into Lichii's default Windows mod
directory. The command requires a matching NUP or an extracted `--nso main`
before installation. It checks the table checksum, executable checksum, NSO build
ID, all three original hook instructions, and executable padding bounds. It does not edit
emulator settings. Regenerating replaces only this mod's own patch file.

Generation without game verification is available for reviewing patch bytes;
omit `--game`. Such output still applies only to the build listed above.

## Validation and limits

- Lichii's log confirms the IPS patch is applied to `main`.
- A fresh emulator process loads the installed patch and reaches gameplay.
  The title screen and attract video also run.
- Sixty AArch64 executions cover all three projection paths, five target ratios,
  unchanged non-16:9 cameras, return addresses, all general registers, stack,
  and condition flags.
- A matched Ingot Isle comparison measured horizontal landmark scaling of
  `0.743965` (expected `0.744186`) and vertical scaling of `1.000543`.
  At the matching display ratio this preserves 3D proportions and reveals
  **34.375% more horizontal scene coverage** than 16:9.
- The first revision missed two compiler-inlined projection paths. The corrected
  patch includes both; replace older copies of the mod.
- **Known limitation:** HUD text/icons, videos, and other 2D layouts stretch.
  World-space UI anchors may also need separate correction. Title and loading
  backgrounds can expose clear-color strips beyond their original artwork.
- **Not fully verified:** other layers, bosses, cutscenes, photo mode,
  screen-space effects, and full 32:9 gameplay. Other ratios are generated and
  instruction-tested but do not have the same visual validation as 3440x1440.
- No emulator binary modification is required.

Run validation with:

```powershell
python -m pip install -r requirements-validation.txt
python -m unittest discover -s tests -v
```

See `docs/research.md` for the exact hook and current validation status.

For a stationary-camera screenshot comparison:

```powershell
python tools/compare_views.py before.png after.png --aspect 2.388888889
```
