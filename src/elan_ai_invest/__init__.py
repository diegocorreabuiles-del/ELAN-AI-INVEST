"""ELAN Quantum investment platform."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("elan-ai-invest")
except PackageNotFoundError:
    __version__ = "0+unknown"
