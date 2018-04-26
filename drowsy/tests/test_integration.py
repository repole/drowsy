"""
    drowsy.tests.test_integration
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Integration tests for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from drowsy.parser import ModelQueryParamParser
from drowsy.tests.base import DrowsyTests
from drowsy.tests.resources import *


class DrowsyIntegrationTests(DrowsyTests):

    """General purpose drowsy integration tests."""

    def test_offset(self):
        """Make sure providing an offset query_param works."""
        query_params = {"offset": "1"}
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(result[0]["album_id"] == 2)

    def test_limit(self):
        """Make sure providing a limit query_param works."""
        query_params = {"limit": "1"}
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(len(result) == 1)

    def test_get_resources_ordered(self):
        """Test simple get_resources sort functionality."""
        query_params = {
            "sort": "-album_id,title"
        }
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts()
        )
        self.assertTrue(
            len(result) == 347 and
            result[0]["album_id"] == 347)

    def test_get_first_page(self):
        """Test that we can get the first page of a set of objects."""
        query_params = {
            "sort": "album_id"
        }
        album_resource = AlbumResource(session=self.db_session)
        parser = ModelQueryParamParser(query_params)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 1)

    def test_get_second_page(self):
        """Test that we can get the second page of a set of objects."""
        query_params = {
            "sort": "album_id",
            "page": "2"
        }
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 31)

