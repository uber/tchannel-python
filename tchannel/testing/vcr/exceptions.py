from __future__ import absolute_import


class VCRException(Exception):
    "Base class for exceptions raised by the VCR library."


class RequestNotFoundError(VCRException):
    "Raised when a request doesn't have a recorded response."


class UnsupportedVersionError(VCRException):
    "Raised when the version of a recording is not supported."
