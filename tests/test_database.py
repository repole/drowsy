"""
    tests.test_database
    ~~~~~~~~~~~~~~~~~~~

    Test database checking for Drowsy.

"""
# :copyright: (c) 2016-2025 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from sqlalchemy import select
from .base import DrowsyDatabaseTests
from .models import Album


class TestDrowsyDatabaseConnection(DrowsyDatabaseTests):

    """Database tests to ensure our connection is valid."""

    @staticmethod
    def test_db(db_session):
        """Make sure our test db is functional."""
        stmt = select(Album).where(Album.album_id == 1)
        result = db_session.execute(stmt).scalars().all()
        assert len(result) == 1
        assert result[0].artist_id == 1
