"""
    drowsy.tests.test_integration
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Integration tests for Drowsy.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from drowsy.parser import ModelQueryParamParser
from .base import DrowsyDatabaseTests
from .resources import *


class TestDrowsyIntegration(DrowsyDatabaseTests):

    """General purpose drowsy integration tests."""

    @staticmethod
    def test_offset(db_session):
        """Make sure providing an offset query_param works."""
        query_params = {"offset": "1"}
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=db_session)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        assert result[0]["album_id"] == 2

    @staticmethod
    def test_limit(db_session):
        """Make sure providing a limit query_param works."""
        query_params = {"limit": "1"}
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=db_session)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        assert len(result) == 1

    @staticmethod
    def test_get_resources_ordered(db_session):
        """Test simple get_resources sort functionality."""
        query_params = {
            "sort": "-album_id,title"
        }
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts()
        )
        assert len(result) == 347
        assert result[0]["album_id"] == 347

    @staticmethod
    def test_get_first_page(db_session):
        """Test that we can get the first page of a set of objects."""
        query_params = {
            "sort": "album_id"
        }
        album_resource = AlbumResource(session=db_session)
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
        assert len(result) == 30
        assert result[0]["album_id"] == 1

    @staticmethod
    def test_get_second_page(db_session):
        """Test that we can get the second page of a set of objects."""
        query_params = {
            "sort": "album_id",
            "page": "2"
        }
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=db_session)
        offset_limit_info = parser.parse_offset_limit(page_max_size=30)
        offset = offset_limit_info.offset
        limit = offset_limit_info.limit
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        assert len(result) == 30
        assert result[0]["album_id"] == 31

    @staticmethod
    def test_subresource_nested_query(db_session):
        """Ensure a simple subresource query works."""
        query_params = {
            "tracks._subquery_.track_id-gte": 5,
            "tracks.playlists._subquery_.playlist_id-lte": 5
        }
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            subfilters=parser.parse_subfilters(),
            embeds=parser.parse_embeds()
        )
        success = False
        for album in result:
            if album["album_id"] == 3:
                assert len(album["tracks"]) == 1
                assert album["tracks"][0]["track_id"] == 5
                success = True
        assert success

    @staticmethod
    def test_subresource_simple_query(db_session):
        """Ensure a simple subresource query works."""
        query_params = {
            "tracks._subquery_.track_id-gte": 5,
            "tracks.playlists._subquery_.playlist_id-lte": 5
        }
        parser = ModelQueryParamParser(query_params)
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            subfilters=parser.parse_subfilters(),
            embeds=parser.parse_embeds()
        )
        success = False
        for album in result:
            if album["album_id"] == 3:
                assert len(album["tracks"]) == 1
                assert album["tracks"][0]["track_id"] == 5
                success = True
        assert success
