"""
    drowsy.tests.__init__
    ~~~~~~~~~~~~~~~~~~~~~

    Tests for Drowsy.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import unittest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mqlalchemy.utils import dummy_gettext
from drowsy.exc import (
    UnprocessableEntityError, MethodNotAllowedError, OffsetLimitParseError,
    BadRequestError, ResourceNotFoundError)
from drowsy.tests.resources import *
from drowsy.parser import QueryParamParser
from drowsy.router import ModelResourceRouter
import json
import tempfile
import shutil


class DrowsyTests(unittest.TestCase):

    """A collection of Drowsy` tests."""

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

    def test_db(self):
        """Make sure our test db is functional."""
        result = self.db_session.query(Album).filter(
            Album.album_id == 1).all()
        self.assertTrue(len(result) == 1 and result[0].artist_id == 1)

    def test_simple_patch(self):
        """Make sure that a simple obj update works."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.patch((album.album_id,), {"title": "TEST"})
        self.assertTrue(
            result["title"] == "TEST" and
            album.title == "TEST")

    def test_empty_patch(self):
        """Make sure that a obj update works with no update params."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.patch((album.album_id,), {})
        self.assertTrue(
            result["title"] == album.title)

    def test_list_relation_add_item(self):
        """Make sure that we can add an item to a list relation."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        self.assertTrue(len(playlist.tracks) == 1)
        playlist_resource = PlaylistResource(session=self.db_session)
        update_data = {
            "tracks": [{
                "$op": "add",
                "track_id": "1"
            }]
        }
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        self.assertTrue(
            len(playlist.tracks) == 2 and
            len(result["tracks"]) == 2)

    def test_list_relation_add_new_item(self):
        """Ensure we can add a new obj to a list using relationship."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()[0]
        update_data = {
            "tracks": [{
                "$op": "add",
                "track_id": "4000",
                "name": "Test Track Seven",
                "album": {
                    "album_id": "347",
                },
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }]
        }
        playlist_resource = PlaylistResource(session=self.db_session)
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        self.assertTrue(len(playlist.tracks) == 2 and
                        len(result["tracks"]) == 2 and
                        playlist.tracks[1].composer == "Nick Repole" and
                        result["tracks"][1]["composer"] == "Nick Repole")

    def test_list_relation_update_item(self):
        """Ensure we can update a list relationship item."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        playlist_resource = PlaylistResource(session=self.db_session)
        update_data = {
            "tracks": [{
                "track_id": 597,
                "name": "Test Track Seven"
            }]
        }
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        self.assertTrue(
            playlist.tracks[0].name == "Test Track Seven" and
            result["tracks"][0]["name"] == playlist.tracks[0].name)

    def test_single_relation_item(self):
        """Make sure that a non-list relation can have a field set."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        update_data = {
            "artist": {"name": "TEST"}
        }
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.patch((album.album_id,), update_data)
        self.assertTrue(
            album.artist.name == "TEST" and
            result["artist"]["name"] == album.artist.name)

    def test_single_relation_item_set_fail(self):
        """Ensure we can't set a relation to a non object value."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"artist": 5})

    def test_list_relation_set_fail(self):
        """Ensure we can't set a list relation to a non object value."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"tracks": 5})

    def test_list_relation_non_item_fail(self):
        """Ensure we can't set list relation items to a non object."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"tracks": ["TEST"]})

    def test_list_relation_bad_item_value_fail(self):
        """Ensure list relation item validation works."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaises(
            UnprocessableEntityError,
            album_resource.patch,
            (album.album_id, ),
            {"tracks": [{"bytes": "TEST"}]})

    def test_set_single_relation_item(self):
        """Make sure that a non-list relation can be set."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        update_params = {
            "artist": {"artist_id": 3}
        }
        result = album_resource.patch((album.album_id,), update_params)
        self.assertTrue(
            album.artist.name == "Aerosmith" and
            result["artist"]["name"] == album.artist.name)

    def test_set_single_relation_item_to_none(self):
        """Make sure that a non-list relation can be set to `None`."""
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).all()[0]
        track_resource = TrackResource(session=self.db_session)
        update_params = {
            "genre": None
        }
        result = track_resource.patch((track.track_id,), update_params)
        self.assertTrue(
            track.genre is None and
            result["genre"] is None)

    def test_set_empty_single_relation_item(self):
        """Make sure that an empty non-list relation can be set."""
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).all()[0]
        track.genre = None
        track_resource = TrackResource(session=self.db_session)
        update_data = {
            "genre": {"genre_id": 1}
        }
        result = track_resource.patch((track.track_id, ), update_data)
        self.assertTrue(
            track.genre.name == "Rock" and
            result["genre"]["name"] == track.genre.name)

    def test_list_relation_remove_item(self):
        """Make sure that we can remove an item from a list relation."""
        playlist = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        playlist_resource = PlaylistResource(session=self.db_session)
        update_params = {
            "tracks": [{
                "track_id": 597,
                "$op": "remove"
            }]
        }
        result = playlist_resource.patch(
            (playlist.playlist_id, ), update_params)
        self.assertTrue(
            len(playlist.tracks) == 0 and
            len(result["tracks"]) == 0)

    def test_new_single_relation_item(self):
        """Make sure that a non-list relation can be created."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).first()
        album_resource = AlbumResource(session=self.db_session)
        update_params = {
            "artist": {
                "artist_id": 999,
                "name": "Nick Repole",
            }
        }
        result = album_resource.patch((album.album_id,), update_params)
        # make sure original artist wasn't just edited.
        artist = self.db_session.query(Artist).filter(
            Artist.artist_id == 1).first()
        self.assertTrue(
            album.artist.name == "Nick Repole" and
            result["artist"]["name"] == album.artist.name and
            artist is not None)

    def test_get_collection(self):
        """Test simple get_collection functionality."""
        query_params = {
            "album_id-lt": "10",
            "query": json.dumps({"title": "Big Ones"})
        }
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=QueryParamParser(query_params).parse_filters(
                album_resource.model)
        )
        self.assertTrue(
            len(result) == 1 and
            result[0]["album_id"] == 5
        )

    def test_get_collection_filters(self):
        """Test simple get_collection filtering functionality."""
        query_params = {
            "album_id-lt": "10",
            "title-like": "Big",
            "album_id-gt": 4,
            "album_id-gte": 5,
            "album_id-lte": 5,
            "album_id-eq": 5,
            "album_id": 5,
            "album_id-ne": 6,
            "query": json.dumps({"title": "Big Ones"})
        }
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=QueryParamParser(query_params).parse_filters(
                album_resource.model)
        )
        self.assertTrue(
            len(result) == 1 and
            result[0]["album_id"] == 5
        )

    def test_get_all_objects(self):
        """Test getting all objects with an empty dict of params."""
        query_params = {}
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=QueryParamParser(query_params).parse_filters(
                album_resource.model)
        )
        self.assertTrue(len(result) == 347)

    def test_get_all_objects_null_query(self):
        """Test getting all objects with query_params set to `None`."""
        query_params = None
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=QueryParamParser(query_params).parse_filters(
                album_resource.model)
        )
        self.assertTrue(len(result) == 347)

    def test_get_resources_ordered(self):
        """Test simple get_resources sort functionality."""
        query_params = {
            "sort": "-album_id,title"
        }
        parser = QueryParamParser(query_params)
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
        parser = QueryParamParser(query_params)
        offset, limit = parser.parse_offset_limit(page_max_size=30)
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
        parser = QueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        offset, limit = parser.parse_offset_limit(page_max_size=30)
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 31)

    def test_no_page_max_size_fail(self):
        """Not providing a max page size with page > 1 should fail."""
        query_params = {"page": "2"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit)

    def test_bad_page_num(self):
        """Test that providing a negative page number fails."""
        query_params = {"page": "-1"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit)

    def test_offset(self):
        """Make sure providing an offset query_param works."""
        query_params = {"offset": "1"}
        parser = QueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        offset, limit = parser.parse_offset_limit(page_max_size=30)
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(result[0]["album_id"] == 2)

    def test_offset_fail(self):
        """Make sure providing a bad offset query_param fails."""
        query_params = {"offset": "abcd"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit
        )

    def test_limit(self):
        """Make sure providing a limit query_param works."""
        query_params = {"limit": "1"}
        parser = QueryParamParser(query_params)
        album_resource = AlbumResource(session=self.db_session)
        offset, limit = parser.parse_offset_limit(page_max_size=30)
        result = album_resource.get_collection(
            filters=parser.parse_filters(album_resource.model),
            sorts=parser.parse_sorts(),
            limit=limit,
            offset=offset
        )
        self.assertTrue(len(result) == 1)

    def test_limit_fail(self):
        """Make sure providing a bad limit query_param is ignored."""
        query_params = {"limit": "abcd"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit
        )

    def test_limit_override(self):
        """Ensure providing a page_max_size overrides a high limit."""
        query_params = {"limit": "1000"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit,
            30
        )

    # ROUTER TESTS

    # POST
    def test_router_post(self):
        """Test that posting a resource via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "4000",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }
        ]
        result = router.post("/tracks", data=tracks[0])
        self.assertTrue(
            result["track_id"] == 4000
        )

    def test_router_post_fail(self):
        """Test posting a bad resource via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "ERROR",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }
        ]
        self.assertRaises(
            UnprocessableEntityError,
            router.post,
            path="/tracks",
            data=tracks[0]
        )

    def test_router_post_collection(self):
        """Test that posting a resource list via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "4000",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            },
            {
                "track_id": "4001",
                "name": "Test Track Eight",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }
        ]
        result = router.post("/tracks", data=tracks)
        self.assertTrue(result is None)

    def test_router_post_collection_fail(self):
        """Test posting a bad resource list via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "ERROR",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            },
            {
                "track_id": "4001",
                "name": "Test Track Eight",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }
        ]
        self.assertRaises(
            UnprocessableEntityError,
            router.post,
            path="/tracks",
            data=tracks
        )

    def test_router_post_attr(self):
        """Test that posting a resource attr via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.post("/tracks/14/bytes", data=1)
        self.assertTrue(result == 1)

    def test_router_post_attr_fail(self):
        """Test posting a bad resource attr via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            UnprocessableEntityError,
            router.post,
            path="/tracks/14/bytes",
            data="BAD"
        )

    def test_router_post_ident_fail(self):
        """Test posting to an already identified resource fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            MethodNotAllowedError,
            router.post,
            path="/tracks/14",
            data={}
        )

    def test_router_subresource_post(self):
        """Test that posting a subresource via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "4000",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }
        ]
        result = router.post("/albums/1/tracks", data=tracks[0])
        self.assertTrue(
            len(result) == 11
        )

    def test_router_subresource_post_list(self):
        """Test that posting a subresource list via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "4000",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            },
            {
                "track_id": "4001",
                "name": "Test Track Eight",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            },
        ]
        result = router.post("/albums/1/tracks", data=tracks)
        self.assertTrue(
            len(result) == 12
        )

    def test_router_subresource_post_only_child(self):
        """Test posting a subresource only child via router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        artist = {"name": "Nick Repole"}
        result = router.post("/albums/1/artist", data=artist)
        self.assertTrue(
            result["name"] == "Nick Repole"
        )

    def test_router_subresource_post_fail(self):
        """Test posting a bad subresource via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "ERROR",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            }
        ]
        self.assertRaises(
            UnprocessableEntityError,
            router.post,
            path="/albums/1/tracks",
            data=tracks[0]
        )

    def test_router_subresource_post_list_fail(self):
        """Test posting a bad subresource list via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [
            {
                "track_id": "ERROR",
                "name": "Test Track Seven",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            },
            {
                "track_id": "4001",
                "name": "Test Track Eight",
                "media_type": {
                    "media_type_id": "2"
                },
                "genre": {
                    "genre_id": "10"
                },
                "composer": "Nick Repole",
                "milliseconds": "206009",
                "bytes": "3305166",
                "unit_price": "0.99",
            },
        ]
        self.assertRaises(
            UnprocessableEntityError,
            router.post,
            path="/albums/1/tracks",
            data=tracks
        )

    def test_router_subresource_post_ident_fail(self):
        """Test posting to an already identified resource fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            MethodNotAllowedError,
            router.post,
            path="/albums/1/tracks/14",
            data={}
        )

    def test_router_subresource_post_attr(self):
        """Test that posting a subresource attr via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.post("/albums/1/tracks/14/bytes", data=1)
        self.assertTrue(result == 1)

    def test_router_subresource_post_attr_fail(self):
        """Test posting a bad subresource attr via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            UnprocessableEntityError,
            router.post,
            path="/albums/1/tracks/14/bytes",
            data="BAD"
        )

    # GET

    def test_router_get(self):
        """Test getting an identified resource works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1", query_params=query_params)
        self.assertTrue(
            result["album_id"] == 1
        )

    def test_router_get_not_found(self):
        """Test getting an identified resource fails with bad id."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/1000000",
            query_params=query_params)

    def test_router_get_attr(self):
        """Test getting an identified resource attr works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/title", query_params=query_params)
        self.assertTrue(
            result == "For Those About To Rock We Salute You"
        )

    def test_router_get_attr_not_found(self):
        """Test getting a resource attr fails with bad attr name."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/1/dne",
            query_params=query_params)

    def test_router_get_collection_filtered(self):
        """Test getting a resource collection via a router works."""
        query_params = {
            "album_id-lt": "10",
            "title-like": "Big",
            "album_id-gt": 4,
            "album_id-gte": 5,
            "album_id-lte": 5,
            "album_id-eq": 5,
            "album_id": 5,
            "album_id-ne": 6,
            "query": json.dumps({"title": "Big Ones"})
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params)
        self.assertTrue(
            len(result) == 1 and
            result[0]["album_id"] == 5
        )

    def test_router_get_resource_collection_ordered(self):
        """Test getting an ordered resource collection via a router."""
        query_params = {
            "sort": "-album_id,title"
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params)
        self.assertTrue(
            len(result) == 347 and
            result[0]["album_id"] == 347)

    def test_router_get_resource_collection_first_page(self):
        """Test getting the first page of a resource collection."""
        query_params = {
            "sort": "album_id",
            "limit": 30
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params)
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 1)

    def test_router_get_resource_collection_second_page(self):
        """Test getting the second page of a resource collection."""
        query_params = {
            "sort": "album_id",
            "limit": 30,
            "page": "2"
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params)
        self.assertTrue(
            len(result) == 30 and
            result[0]["album_id"] == 31)

    def test_router_get_resource_collection_bad_page_fail(self):
        """Providing a bad page number fails via a router."""
        query_params = {"page": "2"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums",
            query_params=query_params)

    def test_router_get_resource_collection_offset(self):
        """Providing an offset query_param works via a router."""
        query_params = {"offset": "1"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params)
        self.assertTrue(result[0]["album_id"] == 2)

    def test_router_get_resource_collection_offset_fail(self):
        """Providing a bad offset query_param fails via a router."""
        query_params = {"offset": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums",
            query_params=query_params)

    def test_router_get_resource_collection_offset_no_strict(self):
        """Providing a bad offset query_param ignored via a router."""
        query_params = {"offset": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params, strict=False)
        self.assertTrue(result[0]["album_id"] == 1)

    def test_router_get_resource_collection_limit_fail(self):
        """Providing a bad limit query_param fails via a router."""
        query_params = {"limit": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums",
            query_params=query_params)

    def test_router_get_resource_collection_limit_no_strict(self):
        """Providing a bad limit query_param ignored via a router."""
        query_params = {"limit": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params, strict=False)
        self.assertTrue(result[0]["album_id"] == 1)

    def test_router_get_subresource(self):
        """Test getting an identified subresource works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks/14", query_params=query_params)
        self.assertTrue(
            result["track_id"] == 14
        )

    def test_router_get_subresource_only_child(self):
        """Test getting an only child subresource works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/artist", query_params=query_params)
        self.assertTrue(
            result["artist_id"] == 1
        )

    def test_router_get_subresource_not_found(self):
        """Test getting an identified subresource fails with bad id."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/1/tracks/1000000",
            query_params=query_params)

    def test_router_get_subresource_attr(self):
        """Test getting an identified subresource attr works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks/14/name",
                            query_params=query_params)
        self.assertTrue(
            result == "Spellbound"
        )

    def test_router_get_subresource_attr_not_found(self):
        """Test getting a subresource attr fails with bad attr name."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/1/tracks/14/dne",
            query_params=query_params)

    def test_router_get_subresource_collection_filtered(self):
        """Test getting a subresource collection via a router works."""
        query_params = {
            "track_id-lt": "10",
            "name-like": "Finger",
            "track_id-gt": 5,
            "track_id-gte": 6,
            "track_id-lte": 6,
            "track_id-eq": 6,
            "track_id": 6,
            "track_id-ne": 7,
            "query": json.dumps({"name": "Put The Finger On You"})
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        self.assertTrue(
            len(result) == 1 and
            result[0]["track_id"] == 6
        )

    def test_router_get_subresource_collection_ordered(self):
        """Test getting an ordered subresource collection via router."""
        query_params = {
            "sort": "-track_id,name"
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        self.assertTrue(
            len(result) == 10 and
            result[0]["track_id"] == 14)

    def test_router_get_subresource_collection_first_page(self):
        """Test getting the first page of a subresource collection."""
        query_params = {
            "sort": "track_id",
            "limit": 5
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        self.assertTrue(
            len(result) == 5 and
            result[0]["track_id"] == 1)

    def test_router_get_subresource_collection_second_page(self):
        """Test getting the second page of a subresource collection."""
        query_params = {
            "sort": "track_id",
            "limit": 5,
            "page": "2"
        }
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        self.assertTrue(
            len(result) == 5 and
            result[0]["track_id"] == 10)

    def test_router_get_subresource_collection_bad_page_fail(self):
        """Providing a bad subresource page fails via a router."""
        query_params = {"page": "2"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums/1/tracks",
            query_params=query_params)

    def test_router_get_subresource_collection_offset(self):
        """Providing an offset subresource query_param works."""
        query_params = {"offset": "1"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        self.assertTrue(result[0]["track_id"] == 6)

    def test_router_get_subresource_collection_offset_fail(self):
        """Providing a bad offset subresource query_param fails."""
        query_params = {"offset": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums/1/tracks",
            query_params=query_params)

    def test_router_get_subresource_collection_offset_no_strict(self):
        """Providing a bad offset subresource query_param ignored."""
        query_params = {"offset": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params, strict=False)
        self.assertTrue(result[0]["track_id"] == 1)

    def test_router_get_subresource_collection_limit_fail(self):
        """Providing a bad limit subresource query_param fails."""
        query_params = {"limit": "abcd"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums/1/tracks",
            query_params=query_params)

    # PUT

    def test_router_put(self):
        """Test that putting a resource via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        track = {
            "album": "/tracks/1/album",
            "bytes": 11170334,
            "composer": "Angus Young, Malcolm Young, Brian Johnson",
            "genre": "/tracks/1/genre",
            "media_type": "/tracks/1/media_type",
            "milliseconds": 4000000,
            "name": "For Those About To Rock (We Salute You)",
            "playlists": "/tracks/1/playlists",
            "self": "/tracks/1",
            "track_id": 1,
            "unit_price": 0.99
        }
        result = router.put("/tracks/1", data=track)
        self.assertTrue(
            result["milliseconds"] == 4000000
        )

if __name__ == '__main__':    # pragma: no cover
    unittest.main()
