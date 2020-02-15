"""
    drowsy.__init__
    ~~~~~~~~~~~~~~~

    Root of the Drowsy module.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
import logging
try:
    from logging import NullHandler
except ImportError:  # pragma: no cover
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())


__version__ = "0.0.1dev"
