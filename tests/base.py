"""
    tests.base
    ~~~~~~~~~~

    Commonly used classes and definitions for Drowsy tests.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.


class DrowsyTests:

    """Base class used for set up and tear down of drowsy tests."""


class DrowsyDatabaseTests(DrowsyTests):

    """Base class used for set up and tear down of drowsy tests."""

    backends = ['sqlite', 'mssql', 'postgres']
