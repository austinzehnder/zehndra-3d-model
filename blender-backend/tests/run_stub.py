#!/usr/bin/env python3
"""Run a generated build.py with stubbed bpy/bkit (no Blender needed).

Usage:
  python3 tests/run_stub.py <build.py> [shot ...] [--look day|dusk] [--samples N] [--res WxH]

The script runs end to end against the stubs: scene setup, materials,
every build stage, sky/sun, shots, and the render loop (mocked). The
stub prints the per-stage part counts and flags duplicate part names
and degenerate parts. Exit code is the script's exit code.

Example:
  python3 tests/run_stub.py sample-demo-home-build.py aerial street backyard interior --look day --samples 32 --res 960x540
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUBKIT = os.path.join(HERE, "stubkit")


def main(argv):
    if not argv:
        print("usage: run_stub.py <build.py> [blender args]", file=sys.stderr)
        return 1
    script = argv[0]
    rest = argv[1:]
    env = dict(os.environ)
    env["BLUEPRINT_SKILL_DIR"] = STUBKIT
    env["PYTHONPATH"] = STUBKIT + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, script, "--"] + rest
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
