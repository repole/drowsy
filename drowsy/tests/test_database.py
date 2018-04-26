"""
    drowsy.tests.test_database
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test database checking for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import Album


class DrowsyDatabaseTests(DrowsyTests):

    """Database tests to ensure our connection is valid."""

    def test_db(self):
        """Make sure our test db is functional."""
        result = self.db_session.query(Album).filter(
            Album.album_id == 1).all()
        self.assertTrue(len(result) == 1 and result[0].artist_id == 1)
