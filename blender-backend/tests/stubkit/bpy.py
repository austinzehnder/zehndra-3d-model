"""Minimal bpy stand-in for testing generated build.py scripts.

Accepts any attribute access or call (via MagicMock) so node setup,
light creation, and render calls in the generated script run without
Blender. Nothing renders; nothing is saved.
"""

from unittest.mock import MagicMock

data = MagicMock(name="bpy.data")
context = MagicMock(name="bpy.context")
ops = MagicMock(name="bpy.ops")
