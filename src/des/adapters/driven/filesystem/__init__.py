"""Filesystem driven adapters."""

from des.adapters.driven.filesystem.in_memory_filesystem import InMemoryFileSystem
from des.adapters.driven.filesystem.real_filesystem import RealFileSystem


# Backward compatibility alias
RealFilesystem = RealFileSystem

__all__ = ["InMemoryFileSystem", "RealFileSystem", "RealFilesystem"]
