"""
    drowsy.tests.test_utils
    ~~~~~~~~~~~~~~~~~~~~~~~

    Utility function tests for Drowsy.

    :copyright: (c) 2018-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from mqlalchemy.utils import dummy_gettext
from .schemas import MsAlbumSchema
from drowsy.utils import get_field_by_data_key, get_error_message


def test_get_field_by_data_key():
    """Test get_field_by_data_key works with old style Schema."""
    assert get_field_by_data_key(schema=MsAlbumSchema(), data_key="albumId")


def test_get_error_message():
    """Test simple get_error_message functionality."""
    error_messages = {"test": "The limit provided (%(limit)s) is bad"}
    result = get_error_message(
        key="test",
        error_messages=error_messages,
        gettext=dummy_gettext,
        limit="5")
    assert result == "The limit provided (5) is bad"


def test_get_error_message_no_string():
    """Test get_error_message can return a non string."""
    error_messages = {"test": 5}
    result = get_error_message(
        key="test",
        error_messages=error_messages,
        gettext=dummy_gettext)
    assert result == 5
