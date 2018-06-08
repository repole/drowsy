"""
    drowsy.tests.test_utils
    ~~~~~~~~~~~~~~~~~~~~~~~

    Utility function tests for Drowsy.

    :copyright: (c) 2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from mqlalchemy.utils import dummy_gettext
from drowsy.tests.base import DrowsyTests
from drowsy.tests.schemas import MsAlbumSchema
from drowsy.utils import get_field_by_dump_name, get_error_message


class DrowsyUtilsTests(DrowsyTests):

    """Test drowsy utility methods and classes."""

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

    def test_get_field_by_dump_name(self):
        """Test get_field_by_dump_name works with old style Schema."""
        self.assertTrue(
            get_field_by_dump_name(schema=MsAlbumSchema(), dump_name="albumId")
        )

    def test_get_error_message(self):
        """Test simple get_error_message functionality."""
        error_messages = {"test": "The limit provided (%(limit)s) is bad"}
        result = get_error_message(
            key="test",
            error_messages=error_messages,
            gettext=dummy_gettext,
            limit="5")
        self.assertTrue(result == "The limit provided (5) is bad")

    def test_get_error_message_no_string(self):
        """Test get_error_message can return a non string."""
        error_messages = {"test": 5}
        result = get_error_message(
            key="test",
            error_messages=error_messages,
            gettext=dummy_gettext)
        self.assertTrue(result == 5)
