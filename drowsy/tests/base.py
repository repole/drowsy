"""
    drowsy.tests.base
    ~~~~~~~~~~~~~~~~~

    Commonly used classes and definitions for Drowsy tests.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import unittest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import shutil


class DrowsyTests(unittest.TestCase):

    """Base class used for set up and tear down of drowsy tests."""

    def setUp(self):
        """Configure a db session for the chinook database."""
        self.temp_user_data_path = tempfile.mkdtemp()
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "chinook.sqlite")
        shutil.copy(db_path, self.temp_user_data_path)
        db_path = os.path.join(self.temp_user_data_path, "chinook.sqlite")
        connect_string = "sqlite+pysqlite:///" + db_path
        self.db_engine = create_engine(connect_string)
        self.DBSession = sessionmaker(bind=self.db_engine)
        self.db_session = self.DBSession()

    def tearDown(self):
        """Undo any db changes that weren't committed."""
        self.db_session.expunge_all()
        self.db_session.rollback()

    def assertRaisesCode(self, expected_exception, code, *args, **kwargs):
        """Like assertRaises, but checks the exception for a code attr.

        :param expected_exception:
        :param code:
        :param args:
        :param kwargs:
        :return: None

        """
        try:
            args[0](*args[1:], **kwargs)
            raise AssertionError("Callable executed successfully.")
        except expected_exception as ex:
            self.assertTrue(hasattr(ex, "code"))
            self.assertTrue(ex.code == code)

    def test_assert_raises_code_fail(self):
        """Test assert raises code fails properly."""
        self.assertRaises(
            AssertionError,
            self.assertRaisesCode,
            ValueError,
            "test",
            int,
            1
        )
