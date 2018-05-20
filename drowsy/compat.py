"""
    drowsy.compat
    ~~~~~~~~~~~~~

    Python 2 and 3 compatibility utilities for Drowsy.

    :copyright: (c) 2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
try:
    from contextlib import suppress
except ImportError:  # pragma: no cover
    from contextlib import contextmanager

    @contextmanager
    def suppress(*exceptions):
        try:
            yield
        except exceptions:
            pass
