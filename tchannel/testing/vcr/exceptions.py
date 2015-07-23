from __future__ import absolute_import


class VCRError(Exception):
    "Base class for exceptions raised by the VCR library."


class RequestNotFoundError(VCRError):
    "Raised when a request doesn't have a recorded response."


class UnsupportedVersionError(VCRError):
    "Raised when the version of a recording is not supported."
