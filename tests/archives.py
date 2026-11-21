"""Test multicall and installed archive commands against Python's gzip and tar."""
import gzip
import io
import os
import random
import struct
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zlib

nebox, links = map(Path, sys.argv[1:])


def run(*argv, data=b"", success=True):
    result = subprocess.run(argv, input=data, capture_output=True, timeout=30)
    assert (result.returncode == 0) == success, (argv, result.returncode, result.stderr)
    return result.stdout


def member(data, strategy, level):
    encoder = zlib.compressobj(level, zlib.DEFLATED, 31, 8, strategy)
    return encoder.compress(data) + encoder.flush()


def test_gzip():
    data = bytes(range(256)) * 401
    for raw in (b"", data, random.Random(19052).randbytes(80000)):
        assert gzip.decompress(run(nebox, "gzip", "-c", data=raw)) == raw
    fixed = member(data, zlib.Z_FIXED, 6)
    dynamic = gzip.compress(data)
    stored = member(data, zlib.Z_DEFAULT_STRATEGY, 0)
    assert run(links / "zcat", data=fixed + stored + dynamic) == data * 3
    # A member with FEXTRA, FNAME, FCOMMENT and FHCRC set.
    header = dynamic[:3] + bytes([30]) + dynamic[4:10] + b"\x02\x00abname\x00note\x00"
    crc = struct.pack("<H", zlib.crc32(header) & 0xffff)
    assert run(links / "gunzip", "-c", data=header + crc + dynamic[10:]) == data
    run(links / "gzip", "-t", data=header + bytes([crc[0] ^ 1, crc[1]]) + dynamic[10:], success=False)
    run(links / "gzip", "-t", data=dynamic)
    for offset in (-8, -4):
        broken = bytearray(dynamic)
        broken[offset] ^= 1
        run(nebox, "gunzip", "-c", data=broken, success=False)
    run(links / "gzip", "-t", data=dynamic[:-1], success=False)
    run(links / "gzip", "-c", ".", success=False)
    Path("keep").write_bytes(b"existing")
    Path("keep.gz").write_bytes(dynamic[:-1])
    run(nebox, "gunzip", "-f", "keep.gz", success=False)
    assert Path("keep").read_bytes() == b"existing"
    assert Path("keep.gz").read_bytes() == dynamic[:-1]
    Path("payload").write_bytes(data)
    Path("payload.gz").write_bytes(b"existing")
    run(links / "gzip", "payload", success=False)
    assert Path("payload").read_bytes() == data
    assert Path("payload.gz").read_bytes() == b"existing"
    run(links / "gzip", "-f", "payload")
    assert not Path("payload").exists()
    assert gzip.decompress(Path("payload.gz").read_bytes()) == data
    run(links / "gunzip", "payload.gz")
    assert Path("payload").read_bytes() == data and not Path("payload.gz").exists()


def test_tar():
    Path("bin").mkdir()
    exe = Path("bin/tool")
    payload = bytes(range(256)) * 701
    exe.write_bytes(payload)
    exe.chmod(0o755)
    Path("bin/alias").symlink_to("tool")
    # Installer tarballs use pax extended headers for subsecond timestamps.
    with tarfile.open("fixture.tgz", "w:gz", format=tarfile.PAX_FORMAT) as archive:
        archive.add("bin")
        long_name = "resources/" + "p" * 120
        entry = tarfile.TarInfo(long_name)
        entry.size = 3
        archive.addfile(entry, io.BytesIO(b"pax"))
    Path("stage").mkdir()
    run(links / "tar", "-xzf", "fixture.tgz", "-C", "stage")
    assert (Path("stage") / long_name).read_bytes() == b"pax"
    assert Path("stage/bin/tool").read_bytes() == payload
    assert os.access("stage/bin/tool", os.X_OK)
    assert os.readlink("stage/bin/alias") == "tool"
    listed = run(nebox, "tar", "-tzf", "fixture.tgz").splitlines()
    assert b"bin/tool" in listed and b"bin/alias" in listed
    if os.geteuid() != 0:
        archive_data = Path("fixture.tgz").read_bytes()
        root = Path.cwd()
        Path("search-only").mkdir(mode=0o111)
        os.chdir("search-only")
        try:
            assert run(nebox, "tar", "-tzf", "-", data=archive_data).splitlines() == listed
        finally:
            os.chdir(root)
            Path("search-only").chmod(0o700)
    for args, mode in (("-cf", "r:"), ("-czf", "r:gz")):
        output = run(links / "tar", args, "-", "bin")
        with tarfile.open(fileobj=io.BytesIO(output), mode=mode) as archive:
            assert archive.extractfile("bin/tool").read() == payload
            assert archive.getmember("bin/tool").mode & 0o111
            assert archive.getmember("bin/alias").linkname == "tool"
    broken = bytearray(Path("fixture.tgz").read_bytes())
    broken[-8] ^= 1
    run(nebox, "tar", "-tzf", "-", data=broken, success=False)
    with tarfile.open("bad.tar", "w") as archive:
        archive.addfile(tarfile.TarInfo("../outside"))
    run(nebox, "tar", "-xf", "bad.tar", "-C", "stage", success=False)
    assert not Path("outside").exists()
    Path("outside-dir").mkdir()
    Path("stage/resources-link").symlink_to("../outside-dir", target_is_directory=True)
    with tarfile.open("bad.tar", "w") as archive:
        archive.addfile(tarfile.TarInfo("resources-link/file"))
    run(nebox, "tar", "-xf", "bad.tar", "-C", "stage", success=False)
    assert not Path("outside-dir/file").exists()
    corrupt = bytearray(Path("bad.tar").read_bytes())
    corrupt[0] ^= 1
    run(links / "tar", "-tf", "-", data=corrupt, success=False)


with tempfile.TemporaryDirectory() as temp:
    os.chdir(temp)
    test_gzip()
    test_tar()
print("Nebox archives passed gzip framing, tar interoperability, links and invalid inputs")
