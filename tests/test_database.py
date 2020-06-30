"""
    drowsy.tests.test_database
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Test database checking for Drowsy.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from .base import DrowsyDatabaseTests
from .models import Album


class TestDrowsyDatabaseConnection(DrowsyDatabaseTests):

    """Database tests to ensure our connection is valid."""

    @staticmethod
    def test_db(db_session):
        """Make sure our test db is functional."""
        result = db_session.query(Album).filter(
            Album.album_id == 1).all()
        assert len(result) == 1
        assert result[0].artist_id == 1
