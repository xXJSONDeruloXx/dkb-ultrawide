# Research and validation

## Local setup

The initial session was paused in an Ingot Isle dialogue scene. The original
output was 16:9, surrounded by black bars. The monitor reports 3440×1440.

The NUP contains base, update, and DLC package entries. Lichii loads the highest
update's ExeFS. The main build ID above comes from its NSO header and agrees with
the emulator's loader log. Base main has a different build and is unsupported.

Local scratch extraction, saves, original settings, and cloned emulator source
are under `.local/`, excluded from Git. Never distribute those game files.

## Patch location

All offsets below are relative to the decompressed main memory image.
IPS32 records add `0x100` for Lichii's NSO header prefix.

| Offset | Purpose |
| --- | --- |
| `0x158D3F8` | Perspective projection matrix calculation |
| `0x158D404` | Hooked `ldp s1, s2, [x0, #0xAC]` |
| `0x1B7E500` | 44-byte trampoline in executable page padding |
| `0x1B7E460` | Original text segment end; next segment starts `0x1B7F000` |
| object `+0xA0` | Vertical FOV |
| object `+0xAC` | Tangent of half vertical FOV |
| object `+0xB0` | Perspective aspect ratio |

The trampoline replays the original load. If s2 is exactly the original float32
16/9 (`0x3FE38E39`), it replaces s2 with the target float and writes that value
back to object+0xB0. It returns to the original next instruction. Cube and 4:3
projection cameras bypass the change. The 16:9 check uses integer comparison;
no floating-point exception state is changed by comparison.

The original routine keeps w8=-1 live, so the trampoline uses caller-saved w9
and w10. The conditional branch stays inside the trampoline; the longer return
uses AArch64's unconditional branch range. The hook has no stack or link-register
effects. Instruction execution tests exercise both paths.

Writing back aspect should let subsequent frustum calculations see the expanded
view. Actual edge culling remains a visual test item; this is a hypothesis until
gameplay checks are completed.

## Runtime evidence so far

Lichii build 70 logged:

```text
Patching NSO for name=main, build_id=E25C90C1C136638885659FD55BF8A03B3403489D
Applying IPS patch from mod "DKB Ultrawide"
```

The patched game booted to the title screen and attract video. This establishes
loading/boot compatibility, not successful ultrawide gameplay.

Enabling the emulator's GDB stub initially selected the overlay applet, because
its debugger selects the last process. Disabling the overlay applet temporarily
allowed the actual game to be inspected. Both changes are diagnostic only; the
distributed patch needs neither. The debugger was disabled again after installing
the mod. The user subsequently accepted the Windows firewall prompt. No firewall
permission was granted by the agent. The saved game was then loaded successfully
with the mod present. Wider gameplay framing and 2D correction are still pending
a controlled before/after comparison; filling the output alone does not establish
correct ultrawide rendering.

The original global emulator configuration, including the controller mapping and
overlay setting, was restored after debugging. The game-specific output setting
is Stretch and the 3440×1440 candidate is installed. A fullscreen launch is left
ready for further testing. Original global and game-specific settings and the
original save backup remain under `.local/`.

## Next runtime checks

1. Return to the saved Ingot Isle scene in fullscreen and capture stock 16:9.
2. Restart with the aspect patch at the same camera position; compare vertical
   landmarks and newly visible horizontal geometry.
3. Check character proportions at the matching output ratio.
4. Rotate/move the camera and check scenery near the added edges.
5. Test dialogue, pause/menu, transitions, photo mode, and effects.
6. Correct 2D layouts as needed before claiming a complete ultrawide mod.
7. Repeat at nominal 21:9 and 32:9; mark each ratio's actual validation scope.

## Emulator source used

[Lichii](https://github.com/zortos293/Lichii), inspected locally at nx2 commit
`c9ebb5c3af672a0472ca0811392f04fab10203ab`. Relevant source: `src/core/file_sys/nup_container.cpp`,
`src/core/loader/nup.cpp`, `src/core/loader/nso.cpp`,
`src/core/file_sys/patch_manager.cpp`, `src/core/file_sys/ips_layer.cpp`,
`src/core/frontend/framebuffer_layout.cpp`, and `src/core/debugger/`.
