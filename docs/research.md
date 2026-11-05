# Research and validation

## Local setup

The initial session was paused in an Ingot Isle dialogue scene. The original
output was 16:9, surrounded by black bars. The monitor reports 3440×1440.

The NUP contains base, update, and DLC package entries. Lichii loads the highest
update's ExeFS. The main build ID above comes from its NSO header and agrees with
the emulator's loader log. Base main has a different build and is unsupported.

Local scratch extraction, saves, original settings, and cloned emulator source
are under `.local/`, excluded from Git. Never distribute those game files.

## Corrected projection hooks

Offsets are relative to the decompressed main memory image; IPS32 adds the
0x100-byte NSO header. The first revision covered only the standalone virtual
implementation and did not change the active gameplay view. Inspection found
compiler-devirtualized copies that calculate the matrix directly.

| Instruction offset | Object register | Tangent/aspect | Trampoline |
| --- | --- | --- | --- |
| `0x158D404` | x0 | s1 / s2 | `0x1B7E500` |
| `0x82BB4` | x19 | s3 / s4 | `0x1B7E580` |
| `0xB14D0` | x0 | s3 / s4 | `0x1B7E600` |

Each 68-byte trampoline replays its original load and replaces exactly float32
16/9 with the requested aspect. It also writes object+0xB0, used by subsequent
frustum calculations. Other perspective aspects pass through unchanged.
Scratch x9/x10/x11, SP, and NZCV are saved and restored, including on the bypass
path. Vertical FOV at object+0xA0 and its half-angle tangent at +0xAC are unchanged.
All trampolines fit in executable page padding after text end `0x1B7E460` and
before the next segment at `0x1B7F000`.

Sixty Unicorn AArch64 executions cover all three entry points, five target ratios,
and four starting aspect values. They check output, return address, every general
register, unrelated SIMD registers, object writes, stack balance, and condition flags. NSO verification checks all original
hook instructions and the executable padding boundary.

## Matched-view validation: 3440x1440

The same stationary Ingot Isle camera was captured before and after activating
the corrected inlined hooks. The first image has the original 16:9 projection
stretched to the display. The second has the corrected 43:18 projection.
The native emulator captures are 5760x3240 (3x docked rendering); comparison
previews resize them to 1720x720, matching fullscreen presentation at half scale.
They are diagnostic captures, not generated imagery.

SIFT feature matching and affine RANSAC on static scenery yielded 151 candidate
matches and 98 inliers. The measured mapping was:

```text
x_after = 0.743965*x_before - 0.000288*y_before + 246.033671
y_after = 0.000199*x_before + 1.000543*y_before - 0.341626
```

Coordinates above use 1920x1080 analysis images. Expected x scale is 0.744186
and y scale is 1. Live camera matrices independently changed horizontal scale
from 1.357995 to 1.010601 while vertical scale stayed 2.414213. This establishes
horizontal expansion with preserved vertical FOV, rather than a uniformly
zoomed-out or merely stretched image. Coverage increases by 34.375% horizontally.
The added left rock wall, right cave columns, and foreground platform are visible.
The selected view shows geometry in the newly exposed regions; this is not a
claim that every game's culling/effect path is corrected.

The 2D HUD did not receive this correction and remains horizontally stretched.
Speech markers can also retain their old screen positions. A full 2D layout
correction remains future work. Title-screen background edges can expose clear
background beyond the original artwork.

The numeric comparison is in `evidence/measurement.json`. Local PNG captures in
`evidence/` are ignored by Git. The reproducible analysis tool is `tools/compare_views.py`.

A fresh Lichii process subsequently loaded the corrected IPS from disk; its
loader log reported the mod applied to main. The user entered gameplay in the
cave from the title screen. No live code modification was used in this process.
The title and loading screens expose background edges, as noted above.
Automated camera-pan checks were paused when the user took over testing, so
full rotation/culling coverage is still pending.

## Emulator test setup

Enabling the GDB stub initially selected the overlay applet because the debugger
chooses the last process. Disabling the overlay applet allowed game inspection.
Restoring the overlay applet
reproduced a startup stall, so it is disabled during these tests; this is an
emulator workaround, not part of the patch. Original settings and saves are in
`.local/`. The original NUP is never rewritten.

During navigation checks, render resolution is temporarily reduced from 3x to 1x
and keyboard controls are temporarily configured. The distributed patch requires
neither a debugger nor keyboard controls.

## Remaining coverage

HUD/2D layout correction, other layers, bosses, photo mode, all cutscenes, and
screen-space effects need further work. Other ratios have generated patches and
instruction execution checks, but full 32:9 gameplay has not been visually
validated on a matching display.

## Emulator source used

[Lichii](https://github.com/zortos293/Lichii), inspected locally at nx2 commit
`c9ebb5c3af672a0472ca0811392f04fab10203ab`. Relevant source: `src/core/file_sys/nup_container.cpp`,
`src/core/loader/nup.cpp`, `src/core/loader/nso.cpp`,
`src/core/file_sys/patch_manager.cpp`, `src/core/file_sys/ips_layer.cpp`,
`src/core/frontend/framebuffer_layout.cpp`, and `src/core/debugger/`.
