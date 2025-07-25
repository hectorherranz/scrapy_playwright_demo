from .base import PageSink
from .file import FileSink
from .registry import build_sink
from .fake import FakeSink

__all__ = ["PageSink", "FileSink", "build_sink", "FakeSink"]