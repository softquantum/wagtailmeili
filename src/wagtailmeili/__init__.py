from .version import get_version


# release must be one of alpha, beta, rc, or final
VERSION = (0, 4, 0, "beta", 0)

__version__ = get_version(VERSION)
