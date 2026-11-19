"""Exercise clean, incremental and failed builds with the standalone runner."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run(binary, root, *targets, error=None, jobs=None):
    options = [] if jobs is None else ["-j", str(jobs)]
    result = subprocess.run(
        [binary, *options, "build.ne", *targets], cwd=root, capture_output=True, text=True
    )
    if error is None:
        assert result.returncode == 0, result
    else:
        assert result.returncode == 1 and error in result.stderr, result
    return result.stdout.splitlines()


def main(binary, root):
    source = root / "source"
    source.write_text("first\n")
    manifest = root / "build.ne"
    graph = (
        "default final\n"
        "build final middle\n\tcp middle final\n"
        "build middle source\n\tcp source middle\n"
        "build unused missing\n\tfalse\n"
    )
    manifest.write_text(graph)
    assert run(binary, root) == ["cp source middle", "cp middle final"]
    assert (root / "final").read_text() == "first\n"
    assert run(binary, root) == []

    source.write_text("second\n")
    assert run(binary, root) == ["cp source middle", "cp middle final"]
    assert (root / "final").read_text() == "second\n"
    assert run(binary, root) == []
    (root / "middle").unlink()
    assert run(binary, root, "middle") == ["cp source middle"]
    assert run(binary, root) == ["cp middle final"]

    # A different declared input invalidates the edge even when it is older.
    extra = root / "extra"
    extra.touch()
    os.utime(extra, ns=(1, 1))
    manifest.write_text(graph.replace("middle source", "middle source extra"))
    assert run(binary, root) == ["cp source middle", "cp middle final"]

    manifest.write_text(graph.replace("cp source middle", "printf partial > middle; false"))
    run(binary, root, error="command failed for middle")
    assert (root / "middle").read_text() == "partial"
    manifest.write_text(graph)
    assert run(binary, root) == ["cp source middle", "cp middle final"]
    assert (root / "final").read_text() == "second\n"

    run(binary, root, "unused", error="missing input missing for unused")
    run(binary, root, "unknown", error="unknown target unknown")
    manifest.write_text(graph.replace("middle source", "middle final"))
    run(binary, root, error="dependency cycle")
    manifest.write_text(graph + "build middle\n\tfalse\n")
    run(binary, root, error="duplicate output middle")
    manifest.write_text("default absent\nbuild absent\n\ttrue\n")
    run(binary, root, error="command did not produce file absent")
    command = "while [ ! -f resume ]; do sleep 0.01; done; touch locked"
    manifest.write_text("default locked\nbuild locked\n\t" + command + "\n")
    with subprocess.Popen(
        [binary, "build.ne"], cwd=root, stdout=subprocess.PIPE, text=True
    ) as active:
        try:
            assert active.stdout.readline().rstrip() == command
            run(binary, root, error="cannot lock build directory")
        finally:
            (root / "resume").touch()
        assert active.wait(timeout=10) == 0

    run(binary, root, jobs=0, error="job count must be positive")
    run(binary, root, jobs="two", error="invalid job count")

    manifest.write_text(
        "default joined\nbuild joined left right\n\tcat left right > joined\n"
        + "".join(
            f"build {name}\n\ttouch {name}.ready; while [ ! -f release ]; "
            f"do sleep 0.01; done; printf {name} > {name}\n"
            for name in ("left", "right")
        )
    )
    with subprocess.Popen([binary, "-j", "2", "build.ne"], cwd=root) as active:
        try:
            deadline = time.monotonic() + 10
            while not all((root / f"{name}.ready").is_file() for name in ("left", "right")):
                assert time.monotonic() < deadline, "independent jobs did not overlap"
                time.sleep(0.01)
            assert not (root / "joined").exists()
        finally:
            (root / "release").touch()
        assert active.wait(timeout=10) == 0
    assert (root / "joined").read_text() == "leftright"
    assert run(binary, root, jobs=2) == []

    manifest.write_text(
        "default blocked\nbuild blocked broken survivor\n\ttouch blocked\n"
        "build broken\n\tfalse\nbuild survivor\n\tsleep 0.05; touch survivor\n"
    )
    run(binary, root, jobs=2, error="command failed for broken")
    assert (root / "survivor.nebuild-command").is_file()
    assert not (root / "blocked").exists()

    print("nebuild clean, incremental, target selection, parallel jobs, locking, and failure recovery passed")


with tempfile.TemporaryDirectory(prefix="nebuild-") as directory:
    main(str(Path(sys.argv[1]).resolve()), Path(directory))
