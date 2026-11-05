import struct
import unittest

from dkb_ultrawide import HOOKS, ips32, patch_records, ratio_value, verify_nso


class PatchTests(unittest.TestCase):
    def test_ips_targets_decompressed_nso_with_header(self):
        patch = ips32(patch_records(43 / 18))
        self.assertEqual(patch[:5], b"IPS32")
        self.assertEqual(patch[-4:], b"EEOF")
        pos = 5
        for address, payload in patch_records(43 / 18):
            offset, length = struct.unpack_from(">IH", patch, pos)
            self.assertEqual(offset, address + 0x100)
            self.assertEqual(length, len(payload))
            self.assertEqual(patch[pos + 6:pos + 6 + length], payload)
            pos += 6 + length
        self.assertEqual(pos, len(patch) - 4)

    def test_rejects_other_game_build(self):
        nso = bytearray(256)
        nso[:4] = b"NSO0"
        with self.assertRaisesRegex(ValueError, "Unsupported main build"):
            verify_nso(nso)

    def test_resolution_ratios(self):
        self.assertEqual(ratio_value("3440:1440"), 43 / 18)
        self.assertEqual(ratio_value("2560/1080"), 64 / 27)
        self.assertEqual(ratio_value("32:9"), 32 / 9)

    def test_arm64_execution(self):
        try:
            from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM
            from unicorn.arm64_const import UC_ARM64_REG_PC, UC_ARM64_REG_CPACR_EL1
        except ImportError:
            self.skipTest("Install unicorn for actual AArch64 execution checks")
        import unicorn.arm64_const as regs
        for ratio in [21 / 9, 43 / 18, 64 / 27, 32 / 9, 16 / 10]:
            for old in [16 / 9, 1.0, 4 / 3, ratio]:
                for hook, cave, base, tangent, aspect in HOOKS:
                    with self.subTest(ratio=ratio, old=old, hook=hex(hook)):
                        cpu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
                        cpu.mem_map(0x80000, 0x1C00000)
                        cpu.mem_map(0x10000, 0x1000)
                        cpu.mem_map(0x20000, 0x2000)
                        for address, data in patch_records(ratio):
                            cpu.mem_write(address, data)
                        cpu.mem_write(0x100AC, struct.pack("<2f", .41421357, old))
                        cpu.mem_write(0x100A0, struct.pack("<f", .7853982))
                        original_object = bytes(cpu.mem_read(0x10000, 0xC0))
                        for i in range(32):
                            cpu.reg_write(getattr(regs, f"UC_ARM64_REG_Q{i}"), 0x123456789ABCDEF + i)
                        initial = {}
                        for i in range(31):
                            reg = getattr(regs, f"UC_ARM64_REG_X{i}")
                            value = 0x10000 if i == base else 0x12340000 + i
                            initial[reg] = value
                            cpu.reg_write(reg, value)
                        cpu.reg_write(regs.UC_ARM64_REG_SP, 0x21000)
                        cpu.reg_write(regs.UC_ARM64_REG_NZCV, 0xA0000000)
                        cpu.reg_write(UC_ARM64_REG_CPACR_EL1, 3 << 20)
                        cpu.emu_start(hook, hook + 4, count=40)
                        expected = ratio if old == 16 / 9 else old
                        self.assertAlmostEqual(struct.unpack("<f", cpu.mem_read(0x100B0, 4))[0], expected, places=6)
                        simd = cpu.reg_read(getattr(regs, f"UC_ARM64_REG_Q{aspect}")) & 0xFFFFFFFF
                        self.assertAlmostEqual(struct.unpack("<f", struct.pack("<I", simd))[0], expected, places=6)
                        self.assertAlmostEqual(struct.unpack("<f", cpu.mem_read(0x100AC, 4))[0], .41421357, places=6)
                        expected_object = bytearray(original_object)
                        struct.pack_into("<f", expected_object, 0xB0, expected)
                        self.assertEqual(bytes(cpu.mem_read(0x10000, 0xC0)), expected_object)
                        for i in range(32):
                            value = cpu.reg_read(getattr(regs, f"UC_ARM64_REG_Q{i}"))
                            if i == tangent:
                                self.assertEqual(value, struct.unpack("<I", struct.pack("<f", .41421357))[0])
                            elif i != aspect:
                                self.assertEqual(value, 0x123456789ABCDEF + i)
                        for reg, value in initial.items():
                            self.assertEqual(cpu.reg_read(reg), value)
                        self.assertEqual(cpu.reg_read(regs.UC_ARM64_REG_SP), 0x21000)
                        self.assertEqual(cpu.reg_read(regs.UC_ARM64_REG_NZCV), 0xA0000000)
                        self.assertEqual(cpu.reg_read(UC_ARM64_REG_PC), hook + 4)

if __name__ == "__main__":
    unittest.main()
