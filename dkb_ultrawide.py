"""Build a version-checked Donkey Kong Bananza camera aspect patch for Lichii."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct

TITLE_ID = "040074A01BF12000"
BUILD_ID = "E25C90C1C136638885659FD55BF8A03B3403489D000000000000000000000000"
HOOK = 0x158D404
CAVE = 0x1B7E500
ORIGINAL = bytes.fromhex("0188552d")  # ldp s1, s2, [x0, #0xac]
MOD_NAME = "DKB Ultrawide"
# (instruction, trampoline, object register, tangent register, aspect register)
# The compiler devirtualizes the same calculation at two gameplay call sites.
HOOKS = [
    (HOOK, CAVE, 0, 1, 2),
    (0x82BB4, CAVE + 0x80, 19, 3, 4),
    (0xB14D0, CAVE + 0x100, 0, 3, 4),
]


def original_load(base, tangent, aspect):
    return 0x2D400000 | ((0xAC // 4) << 15) | (aspect << 10) | (base << 5) | tangent


def ratio_value(text):
    parts = text.replace("/", ":").split(":")
    try:
        value = float(parts[0]) / float(parts[1]) if len(parts) == 2 else float(text)
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError("Use WIDTH:HEIGHT, e.g. 3440:1440 or 21:9")
    if not math.isfinite(value) or not 1 <= value <= 8:
        raise argparse.ArgumentTypeError("Aspect ratio must be between 1:1 and 8:1")
    return value


def branch(source, target):
    delta = target - source
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError("AArch64 branch out of range")
    return struct.pack("<I", 0x14000000 | ((delta // 4) & 0x3FFFFFF))


def patch_records(ratio):
    bits = struct.unpack("<I", struct.pack("<f", ratio))[0]
    records = []
    for hook, cave, base, tangent, aspect in HOOKS:
        # Preserve every scratch GPR and NZCV: the two inlined paths run inside
        # larger functions. Only the originally loaded SIMD registers change.
        words = [
            0xA9BE2BE9,  # stp x9, x10, [sp, #-32]!
            0xF9000BEB,  # str x11, [sp, #16]
            0xD53B420B,  # mrs x11, nzcv
            original_load(base, tangent, aspect),
            0x1E260009 | (aspect << 5),  # fmov w9, sAspect
            0x5291C72A,  # mov w10, #0x8e39
            0x72A7FC6A,  # movk w10, #0x3fe3, lsl #16 (16/9)
            0x6B0A013F,  # cmp w9, w10
            0x540000A1,  # b.ne cave+0x34
            0x52800009 | ((bits & 0xFFFF) << 5),
            0x72A00009 | ((bits >> 16) << 5),
            0x1E270120 | aspect,  # fmov sAspect, w9
            0xBD00B000 | (base << 5) | aspect,  # str sAspect, [xBase,#0xb0]
            0xD51B420B,  # msr nzcv, x11
            0xF9400BEB,  # ldr x11, [sp, #16]
            0xA8C22BE9,  # ldp x9, x10, [sp], #32
        ]
        body = struct.pack("<16I", *words) + branch(cave + 64, hook + 4)
        records.extend([(hook, branch(hook, cave)), (cave, body)])
    return records


def ips32(records):
    # Lichii patches an NSO header followed by the decompressed memory image.
    return b"IPS32" + b"".join(
        struct.pack(">IH", offset + 0x100, len(data)) + data
        for offset, data in records
    ) + b"EEOF"


def verify_nso(nso):
    if nso[:4] != b"NSO0" or len(nso) < 0x100:
        raise ValueError("Expected an NSO executable")
    build = nso[0x40:0x60].hex().upper()
    if build != BUILD_ID:
        raise ValueError(f"Unsupported main build {build}; expected {BUILD_ID}")
    flags = struct.unpack_from("<I", nso, 12)[0]
    offset, address, size = struct.unpack_from("<III", nso, 16)
    compressed = struct.unpack_from("<I", nso, 96)[0]
    if address != 0 or not HOOK + 4 <= size <= CAVE:
        raise ValueError("Unexpected text layout")
    if max(cave + 68 for _, cave, *_ in HOOKS) > ((size + 4095) & ~4095):
        raise ValueError("Code cave is outside executable page padding")
    if flags & 1:
        import lz4.block
        text = lz4.block.decompress(nso[offset:offset + compressed], uncompressed_size=size)
    else:
        text = nso[offset:offset + size]
    if len(text) != size:
        raise ValueError("Text segment size mismatch")
    for hook, _, base, tangent, aspect in HOOKS:
        if text[hook:hook + 4] != struct.pack("<I", original_load(base, tangent, aspect)):
            raise ValueError(f"Hook instruction at {hook:#x} does not match this build")
    return build


def main_from_nup(path):
    """Read only the best update's main executable; never rewrite the NUP."""
    with Path(path).open("rb") as f:
        header = f.read(128)
        if len(header) != 128 or header[:4] != b"NUP\1":
            raise ValueError("Expected a NUP v1 container")
        toc_offset, toc_size = struct.unpack_from("<QQ", header, 8)
        file_size = f.seek(0, 2)
        if not 0 < toc_size <= 128 * 1024 * 1024 or toc_offset + toc_size > file_size:
            raise ValueError("Invalid NUP table size")
        f.seek(toc_offset)
        toc = f.read(toc_size)
        if hashlib.sha256(toc).digest() != header[24:56]:
            raise ValueError("NUP table checksum mismatch")
        magic, count, dirs, files, pool_offset, pool_size, _ = struct.unpack_from("<IIQQQQQ", toc)
        needed = 48 + count * 64 + dirs * 24 + files * 80
        if magic != 0x01434F54 or not needed <= pool_offset <= toc_size - pool_size:
            raise ValueError("Invalid NUP table")
        packages = [struct.unpack_from("<QIIIIBB", toc, 48 + i * 64) for i in range(count)]
        candidates = [p for p in packages if p[0] == int(TITLE_ID, 16) and p[5] in (0, 1) and p[2] != 0xFFFFFFFF]
        if not candidates:
            raise ValueError("Container has no Donkey Kong Bananza executable")
        package = max(candidates, key=lambda p: (p[5], p[4]))
        if package[2] >= dirs:
            raise ValueError("Invalid ExeFS directory")
        directory_offset = 48 + count * 64 + package[2] * 24
        _, _, first, length, _ = struct.unpack_from("<IIIIQ", toc, directory_offset)
        if needed + (first + length) * 4 > pool_offset:
            raise ValueError("Invalid directory children")
        for i in range(first, first + length):
            node = struct.unpack_from("<I", toc, needed + i * 4)[0]
            if not dirs <= node < dirs + files:
                continue
            start = 48 + count * 64 + dirs * 24 + (node - dirs) * 80
            record = toc[start:start + 80]
            name_offset, name_length, size, extent, stored_size = struct.unpack_from("<IIQQQ", record)
            if name_offset + name_length > pool_size:
                raise ValueError("Invalid file name")
            name = toc[pool_offset + name_offset:pool_offset + name_offset + name_length]
            if name != b"main":
                continue
            if size > 256 * 1024 * 1024 or extent + stored_size > file_size:
                raise ValueError("Invalid executable extent")
            f.seek(extent)
            data = f.read(stored_size)
            if record[64] == 1:
                import zstandard
                data = zstandard.ZstdDecompressor().decompress(data, max_output_size=size)
            elif record[64] != 0:
                raise ValueError("Unsupported NUP codec")
            if len(data) != size or hashlib.sha256(data).digest() != record[32:64]:
                raise ValueError("Executable checksum mismatch")
            return data
    raise ValueError("Main executable missing")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ratio", type=ratio_value, default=43 / 18)
    parser.add_argument("--game", type=Path, help="NUP to verify before generating/installing")
    parser.add_argument("--nso", type=Path, help="Alternatively verify an extracted main NSO")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--install", action="store_true", help="Install verified patch into Lichii/Eden load directory")
    args = parser.parse_args()
    if args.install and not (args.game or args.nso):
        parser.error("--install requires --game or --nso for build verification")
    try:
        if args.game or args.nso:
            verify_nso(main_from_nup(args.game) if args.game else args.nso.read_bytes())
        patch = ips32(patch_records(args.ratio))
        target = args.output / TITLE_ID / MOD_NAME / "exefs" / (BUILD_ID + ".ips")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(patch)
        manifest = dict(title_id=TITLE_ID, build_id=BUILD_ID, ratio=args.ratio,
                        sha256=hashlib.sha256(patch).hexdigest(),
                        records=[dict(offset=hex(a), bytes=b.hex()) for a, b in patch_records(args.ratio)])
        (args.output / "patch.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"Generated {target} ({args.ratio:.9f}:1)")
        if args.install:
            appdata = os.environ.get("APPDATA")
            if not appdata:
                raise ValueError("APPDATA not set; copy the generated mod to your emulator load directory")
            installed = Path(appdata) / "eden" / "load" / TITLE_ID / MOD_NAME / "exefs" / target.name
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_bytes(patch)
            print(f"Installed {installed}; restart the game to apply")
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
