"""
    drowsy.tests.test_resource
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Resource tests for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import json
from drowsy.exc import (
    UnprocessableEntityError, BadRequestError, MethodNotAllowedError)
from drowsy.parser import ModelQueryParamParser
from drowsy.resource import (
    ResourceABC, NestableResourceABC, SchemaResourceABC, ResourceCollection)
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import Album, Artist, Playlist, Track
from drowsy.tests.resources import (
    AlbumResource, PlaylistResource, TrackResource)


class DrowsyResourceTests(DrowsyTests):

    """Test drowsy resources."""

    # ABSTRACT CLASS TESTS

    def test_resource_abc_get(self):
        """Make sure ResourceABC raises exception on `get`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().get,
            1
        )

    def test_resource_abc_post(self):
        """Make sure ResourceABC raises exception on `post`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().post,
            {}
        )

    def test_resource_abc_patch(self):
        """Make sure ResourceABC raises exception on `patch`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().patch,
            1,
            {}
        )

    def test_resource_abc_put(self):
        """Make sure ResourceABC raises exception on `put`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().put,
            1,
            {}
        )

    def test_resource_abc_delete(self):
        """Make sure ResourceABC raises exception on `delete`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().delete,
            1
        )

    def test_resource_abc_get_collection(self):
        """Make sure ResourceABC raises exception on `get_collection`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().get_collection
        )

    def test_resource_abc_post_collection(self):
        """Make sure ResourceABC raises exception on `post_collection`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().post_collection,
            {}
        )

    def test_resource_abc_patch_collection(self):
        """Make sure ResourceABC raises exception on `patch_collection`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().patch_collection,
            {}
        )

    def test_resource_abc_put_collection(self):
        """Make sure ResourceABC raises exception on `put_collection`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().put_collection,
            {}
        )

    def test_resource_abc_delete_collection(self):
        """Make sure ResourceABC raises exception on `delete_collection`."""
        self.assertRaises(
            NotImplementedError,
            ResourceABC().delete_collection
        )

    def test_nestable_resource_abc_make_resource(self):
        """NestableResourceABC exception on `make_subresource`."""
        self.assertRaises(
            NotImplementedError,
            NestableResourceABC().make_subresource,
            "test"
        )

    def test_schema_resource_abc_make_resource(self):
        """SchemaResourceABC raises exception on `make_schema`."""
        self.assertRaises(
            NotImplementedError,
            SchemaResourceABC().make_schema
        )

    def test_schema_resource_abc_schema_kwargs(self):
        """SchemaResourceABC raises exception on `get_schema_kwargs`."""
        self.assertRaises(
            NotImplementedError,
            getattr(SchemaResourceABC(), "_get_schema_kwargs"),
            "test"
        )

    # RESOURCECOLLECTION TESTS

    def test_resource_collection_class(self):
        """Test the ResourceCollection class."""
        rc = ResourceCollection([1, 2, 3], 100)
        self.assertTrue(rc[0] == 1)
        self.assertTrue(rc.resources_fetched == 3)
        self.assertTrue(rc.resources_available == 100)

    # PATCH TESTS

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

    def test_patch_add_existing_subresource(self):
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

    def test_patch_add_new_subresource(self):
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

    def test_patch_update_existing_list_subresource(self):
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

    # def test_error_translation(self):
    #     """Ensure error message translation works."""
    #     def get_excited(value, **variables):
    #         """Append an exclamation point to any string.
    #
    #         :param str value: String to be translated.
    #
    #         """
    #         return dummy_gettext(value, **variables) + "!"
    #     album = self.db_session.query(Album).filter(
    #         Album.album_id == 1).all()[0]
    #     album_resource = AlbumResource(session=self.db_session,
    #                                    context={"gettext": get_excited})
    #     try:
    #         album_resource.patch(
    #             (album.album_id, ), {"tracks": [{"bytes": 5}]})
    #         # should raise an exception...
    #         self.assertTrue(False)
    #     except UnprocessableEntityError as e:
    #         self.assertTrue(e.errors['tracks'][0]['name'][0].endswith("!"))

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
        self.db_session.commit()
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

    # GET COLLECTION TESTS

    def test_get_collection(self):
        """Test simple get_collection functionality."""
        query_params = {
            "album_id-lt": "10",
            "query": json.dumps({"title": "Big Ones"})
        }
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=ModelQueryParamParser(query_params).parse_filters(
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
            filters=ModelQueryParamParser(query_params).parse_filters(
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
            filters=ModelQueryParamParser(query_params).parse_filters(
                album_resource.model)
        )
        self.assertTrue(len(result) == 347)

    def test_get_all_objects_null_query(self):
        """Test getting all objects with query_params set to `None`."""
        query_params = None
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters=ModelQueryParamParser(query_params).parse_filters(
                album_resource.model)
        )
        self.assertTrue(len(result) == 347)

    # PATCH COLLECTION TESTS

    def test_patch_collection_add(self):
        """Test adding to a collection via patch works."""
        update_data = [
            {
                "$op": "add",
                "playlist_id": 9999,
                "name": "New Test Playlist",
                "tracks": [
                    {
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
                    }
                ]
            }
        ]
        playlist_resource = PlaylistResource(session=self.db_session)
        result = playlist_resource.patch_collection(update_data)
        playlists = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 9999).all()
        self.assertTrue(len(playlists) == 1)
        self.assertTrue(len(playlists[0].tracks) == 1)
        self.assertTrue(result is None)

    def test_patch_collection_remove(self):
        """Test removing from a collection via patch works."""
        update_data = [
            {
                "$op": "remove",
                "playlist_id": 18
            }
        ]
        playlist_resource = PlaylistResource(session=self.db_session)
        result = playlist_resource.patch_collection(update_data)
        playlists = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()
        self.assertTrue(len(playlists) == 0)
        self.assertTrue(result is None)

    def test_patch_collection_update(self):
        """Test updating from a collection via patch works."""
        update_data = [
            {
                "playlist_id": 18,
                "name": "New name"
            }
        ]
        playlist_resource = PlaylistResource(session=self.db_session)
        result = playlist_resource.patch_collection(update_data)
        playlists = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()
        self.assertTrue(len(playlists) == 1)
        self.assertTrue(playlists[0].name == "New name")
        self.assertTrue(result is None)

    def test_patch_collection_bad_data(self):
        """Test providing a non list to patch collection fails."""
        update_data = {
            "playlist_id": 18,
            "name": "New name"
        }
        playlist_resource = PlaylistResource(session=self.db_session)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_collection_input",
            playlist_resource.patch_collection,
            update_data
        )

    def test_patch_collection_update_fail(self):
        """Test updating a collection via patch fails validation."""
        update_data = [
            {
                "playlist_id": 18,
                "name": 5
            }
        ]
        playlist_resource = PlaylistResource(session=self.db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "validation_failure",
            playlist_resource.patch_collection,
            update_data
        )

    def test_patch_collection_add_fail(self):
        """Test adding to a collection via patch fails validation."""
        update_data = [
            {
                "$op": "add",
                "playlist_id": 9999,
                "name": 5
            }
        ]
        playlist_resource = PlaylistResource(session=self.db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "validation_failure",
            playlist_resource.patch_collection,
            update_data
        )

    def test_patch_collection_remove_fail(self):
        """Test removing from collection via patch fails validation."""
        update_data = [
            {
                "$op": "remove",
                "playlist_id": "test"
            }
        ]
        playlist_resource = PlaylistResource(session=self.db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "validation_failure",
            playlist_resource.patch_collection,
            update_data
        )

    # PUT COLLECTION TESTS

    def test_put_collection_fail(self):
        """Test that trying to put a collection fails."""
        update_data = []
        playlist_resource = PlaylistResource(session=self.db_session)
        self.assertRaisesCode(
            MethodNotAllowedError,
            "method_not_allowed",
            playlist_resource.put_collection,
            update_data
        )

    # DELETE COLLECTION TESTS

    def test_delete_collection(self):
        """Test deleting from a collection works."""
        filters = {
            "playlist_id": 18
        }
        playlist_resource = PlaylistResource(session=self.db_session)
        result = playlist_resource.delete_collection(filters=filters)
        playlists = self.db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()
        self.assertTrue(len(playlists) == 0)
        self.assertTrue(result is None)
