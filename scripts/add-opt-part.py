#!/usr/bin/env python3
"""Append a small p3 ("/opt") partition to an ophub .img.gz at build time.

R28S-style layout: the image leaves a real partition table entry behind, so the
kernel sees /dev/mmcblkXp3 from the very first boot. The first-boot script then
only has to grow it to the end of the eMMC, format it and mount it -- no MBR
editing on a live, mounted disk.

usage: add-opt-part.py <image.img.gz> [size_mib]
"""
import gzip
import os
import shutil
import struct
import sys
import tempfile

MBR_OFF = 446
ALIGN = 2048  # 1 MiB in 512-byte sectors


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    size_mib = int(sys.argv[2]) if len(sys.argv) > 2 else 256

    tmpdir = tempfile.mkdtemp(prefix="optpart-")
    raw = os.path.join(tmpdir, "disk.img")
    try:
        with gzip.open(path, "rb") as src, open(raw, "wb") as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)

        with open(raw, "r+b") as fh:
            mbr = bytearray(fh.read(512))
            if len(mbr) != 512 or mbr[510:512] != b"\x55\xaa":
                print("not an MBR image, skipped")
                return 0

            entries = []
            for i in range(4):
                ent = mbr[MBR_OFF + 16 * i: MBR_OFF + 16 * (i + 1)]
                start, nsec = struct.unpack("<II", ent[8:16])
                if ent[4] and nsec:
                    entries.append((i, start, nsec))
            if any(i == 2 for i, _, _ in entries):
                print("p3 already present, skipped")
                return 0

            used_end = max((s + n for _, s, n in entries), default=0)
            start = (used_end + ALIGN - 1) // ALIGN * ALIGN
            nsec = size_mib * 1024 * 1024 // 512

            ent = bytearray(16)
            ent[0] = 0x00
            ent[1:4] = b"\xfe\xff\xff"   # CHS start: dummy, LBA only
            ent[4] = 0x83                # Linux
            ent[5:8] = b"\xfe\xff\xff"   # CHS end: dummy
            ent[8:16] = struct.pack("<II", start, nsec)
            mbr[MBR_OFF + 32: MBR_OFF + 48] = ent

            fh.seek(0)
            fh.write(mbr)
            fh.truncate((start + nsec) * 512)

        tmp_gz = path + ".new"
        with open(raw, "rb") as src, gzip.open(tmp_gz, "wb", compresslevel=9) as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
        os.replace(tmp_gz, path)
        print(f"p3 added: start={start} sectors, size={size_mib} MiB -> {path}")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
