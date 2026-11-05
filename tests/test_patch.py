import struct
import unittest

from dkb_ultrawide import BUILD_ID, CAVE, HOOK, ORIGINAL, ips32, patch_records, ratio_value, verify_nso


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
            from unicorn.arm64_const import (UC_ARM64_REG_X0, UC_ARM64_REG_X1,
                UC_ARM64_REG_X8, UC_ARM64_REG_PC, UC_ARM64_REG_CPACR_EL1,
                UC_ARM64_REG_Q0, UC_ARM64_REG_Q1, UC_ARM64_REG_Q2, UC_ARM64_REG_Q3)
        except ImportError:
            self.skipTest("Install unicorn for actual AArch64 execution checks")
        for ratio in [21 / 9, 43 / 18, 64 / 27, 32 / 9, 16 / 10]:
            for old in [16 / 9, 1.0, 4 / 3, ratio]:
                with self.subTest(ratio=ratio, old=old):
                    cpu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
                    cpu.mem_map(0x1000000, 0x2000000)
                    cpu.mem_map(0x10000, 0x1000)
                    for address, data in patch_records(ratio):
                        cpu.mem_write(address, data)
                    cpu.mem_write(0x100AC, struct.pack("<2f", .41421357, old))
                    cpu.reg_write(UC_ARM64_REG_X0, 0x10000)
                    cpu.reg_write(UC_ARM64_REG_X1, 0x12345678)
                    cpu.reg_write(UC_ARM64_REG_X8, 0xFFFFFFFF)
                    cpu.reg_write(UC_ARM64_REG_Q0, 0xABCDEF)
                    cpu.reg_write(UC_ARM64_REG_Q3, 0x123456)
                    cpu.reg_write(UC_ARM64_REG_CPACR_EL1, 3 << 20)
                    cpu.emu_start(HOOK, HOOK + 4, count=30)
                    expected = ratio if old == 16 / 9 else old
                    self.assertAlmostEqual(struct.unpack("<f", cpu.mem_read(0x100B0, 4))[0], expected, places=6)
                    s2 = cpu.reg_read(UC_ARM64_REG_Q2) & 0xFFFFFFFF
                    self.assertAlmostEqual(struct.unpack("<f", struct.pack("<I", s2))[0], expected, places=6)
                    self.assertAlmostEqual(struct.unpack("<f", cpu.mem_read(0x100AC, 4))[0], .41421357, places=6)
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_X8), 0xFFFFFFFF)
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_X1), 0x12345678)
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_Q0), 0xABCDEF)
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_Q3), 0x123456)
                    self.assertEqual(cpu.reg_read(UC_ARM64_REG_PC), HOOK + 4)


if __name__ == "__main__":
    unittest.main()
