from .version import get_version


# release must be one of alpha, beta, rc, or final
VERSION = (0, 3, 3, "final", 0)

__version__ = get_version(VERSION)
