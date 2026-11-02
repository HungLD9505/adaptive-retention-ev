"""Separate research pipelines; preserve imports used by pinned historical readers."""

import importlib
import sys

# Immutable readers retain their original source bytes and module import strings.
# This alias provides import compatibility only; it does not remap files or hashes.
sys.modules[__name__ + ".hung_sprint2"] = importlib.import_module(".supporting_pipeline", __name__)
