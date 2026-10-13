"""Allow running a source checkout without installing it first."""
from pathlib import Path
__path__.append(str(Path(__file__).resolve().parents[1] / "src" / "maxvell"))
__version__ = "0.1.0"
