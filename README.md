# Donkey Kong Bananza ultrawide for Lichii

**Experimental. The patch loads in Lichii; gameplay and visual correctness still need validation.**

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
ID, original hook instruction, and executable padding bounds. It does not edit
emulator settings. Regenerating replaces only this mod's own patch file.

Generation without game verification is available for reviewing patch bytes;
omit `--game`. Such output still applies only to the build listed above.

## Validation and limits

- Lichii's log confirms the IPS patch is applied to `main`.
- The game boots to its title screen and attract video with the patch enabled.
- Twenty AArch64 executions check five target ratios, unchanged non-16:9
  cameras, return addresses, preserved FOV input, and live registers.
- **Not yet verified:** playable 3D framing, edge culling, HUD/text proportions,
  menus, cutscenes, photo mode, screen-space effects, and 32:9 output.
- This patch currently does not correct 2D layouts. HUDs and videos may stretch
  with the emulator output. This is not yet a complete ultrawide presentation.
- No emulator binary modification is required.

Run validation with:

```powershell
python -m pip install unicorn
python -m unittest discover -s tests -v
```

See `docs/research.md` for the exact hook and current validation status.
