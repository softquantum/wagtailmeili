from .version import get_version


# release must be one of alpha, beta, rc, or final
VERSION = (0, 5, 0, "rc", 1)

__version__ = get_version(VERSION)
