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
    UnprocessableEntityError, BadRequestError, MethodNotAllowedError,
    ResourceNotFoundError)
from drowsy.parser import ModelQueryParamParser, SubfilterInfo, SortInfo
from drowsy.resource import (
    ResourceABC, NestableResourceABC, SchemaResourceABC, ResourceCollection)
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import Album, Artist, Playlist, Track
from drowsy.tests.resources import (
    AlbumResource, PlaylistResource, TrackResource, EmployeeResource)


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

    # RESOURCE CLASS TESTS

    def test_resource_session_callable(self):
        """Test that providing a callable session works."""
        def session_callable():
            """Dummy session callable."""
            return self.db_session
        resource = EmployeeResource(session=session_callable)
        self.assertTrue(resource.session is self.db_session)

    def test_resource_session_setter(self):
        """Test setting a session works."""
        resource = EmployeeResource(session=self.db_session)
        new_session = self.DBSession()
        resource.session = new_session
        self.assertTrue(resource.session is not self.db_session)
        self.assertTrue(resource.session is new_session)

    def test_resource_context_callable(self):
        """Test that providing a callable context works."""
        def context_callable():
            """Dummy context callable."""
            return {"test": "test"}
        resource = EmployeeResource(session=self.db_session,
                                    context=context_callable)
        self.assertTrue(resource.context.get("test") == "test")

    def test_resource_context_setter(self):
        """Test setting a resource context works."""
        resource = EmployeeResource(session=self.db_session,
                                    context={})
        resource.context = {"test": "test"}
        self.assertTrue(resource.context.get("test") == "test")

    def test_resource_page_max_size(self):
        """Test that providing a page_max_size works."""
        resource = EmployeeResource(session=self.db_session,
                                    page_max_size=100)
        self.assertTrue(resource.page_max_size == 100)

    def test_resource_page_max_size_0(self):
        """Test that providing 0 for page_max_size works."""
        resource = EmployeeResource(session=self.db_session,
                                    page_max_size=0)
        self.assertTrue(resource.page_max_size is None)

    def test_resource_error_message_override(self):
        """Test that error message overrides are handled properly."""
        resource = EmployeeResource(session=self.db_session)
        try:
            resource.fail(key="invalid_field")
        except BadRequestError as exc:
            self.assertTrue(exc.code == "invalid_field")
            self.assertTrue(exc.message == "Test invalid_field message.")

    def test_resource_make_subresource_fail(self):
        """Test that attempting to make an invalid subresource fails."""
        resource = EmployeeResource(session=self.db_session,
                                    page_max_size=0)
        self.assertRaises(
            ValueError,
            resource.make_subresource,
            "test"
        )

    def test_resource_fail_missing_key(self):
        resource = EmployeeResource(session=self.db_session)
        self.assertRaises(
            AssertionError,
            resource.fail,
            key="test"
        )

    # PATCH TESTS

    def test_patch_simple(self):
        """Make sure that a simple obj update works."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.patch((album.album_id,), {"title": "TEST"})
        self.assertTrue(
            result["title"] == "TEST" and
            album.title == "TEST")

    def test_patch_no_tuple_ident(self):
        """Test passing a single value identity works."""
        album = self.db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.patch(album.album_id, {"title": "TEST"})
        self.assertTrue(
            result["title"] == "TEST" and
            album.title == "TEST")

    def test_patch_empty(self):
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

    def test_patch_subresource_list_add_new(self):
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

    def test_patch_subresource_list_update_existing(self):
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

    def test_patch_subresource_single_update_existing(self):
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

    # GET TESTS

    def test_get(self):
        """Test simple get functionality."""
        resource = AlbumResource(session=self.db_session)
        result = resource.get(1)
        self.assertTrue(result["album_id"] == 1)

    def test_get_with_query(self):
        """Test get with a pre-existing query."""
        query = self.db_session.query(Album).filter(
            Album.title == "test")
        resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            ResourceNotFoundError,
            "resource_not_found",
            resource.get,
            1,
            session=query
        )

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

    def test_get_collection_filters_invalid(self):
        """Test simple get_collection filtering failure."""
        query_params = {
            "query": json.dumps({"title": {"$bad": "Big Ones"}})
        }
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_filters",
            album_resource.get_collection,
            filters=ModelQueryParamParser(query_params).parse_filters(
                album_resource.model
            )
        )

    def test_get_collection_invalid_sorts_type(self):
        """Test non list sorts with get_collection fails."""
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaises(
            ValueError,
            album_resource.get_collection,
            sorts="test"
        )

    def test_get_collection_invalid_sort_type(self):
        """Test non SortInfo sort with get_collection fails."""
        album_resource = AlbumResource(session=self.db_session)
        self.assertRaises(
            ValueError,
            album_resource.get_collection,
            sorts=["test"]
        )

    def test_get_collection_subresource_query(self):
        """Test a subresource query."""
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            subfilters={"tracks": SubfilterInfo(
                filters={'track_id': 1}
            )}
        )
        for album in result:
            for track in album["tracks"]:
                self.assertTrue(
                    track["track_id"] == 1
                )

    def test_get_collection_simple(self):
        """Test getting all objects with an empty dict of params."""
        album_resource = AlbumResource(session=self.db_session)
        result = album_resource.get_collection(
            filters={}
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

    # POST TESTS

    def test_post(self):
        """Test a simple post."""
        data = {"album_id": 9999, "title": "test2", "artist": {"artist_id": 1}}
        resource = AlbumResource(session=self.db_session)
        resource.post(data)
        result = self.db_session.query(Album).filter(
            Album.album_id == 9999).first()
        self.assertTrue(result is not None)

    def test_post_commit_fail(self):
        """Test the commit failure on posts is handled properly."""
        from sqlalchemy.orm import sessionmaker
        DBSession = sessionmaker(bind=self.db_engine, autoflush=False)
        db_session = DBSession()
        new_album = Album(
            album_id=1,
            title="test",
            artist_id=1
        )
        db_session.add(new_album)
        resource = AlbumResource(session=db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "commit_failure",
            resource.post,
            {"album_id": 1, "title": "test2", "artist": {"artist_id": 1}}
        )

    def test_post_commit_fail_already_exists(self):
        """Test the commit fails when the same id already exists."""
        resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "commit_failure",
            resource.post,
            {"album_id": 1, "title": "test2", "artist": {"artist_id": 1}}
        )

    def test_post_collection_no_relation_fail(self):
        """Test a missing non list relation causes a post fail."""
        data = {"title": "test1"}
        resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "validation_failure",
            resource.post,
            data
        )

    # POST COLLECTION TESTS

    def test_post_collection(self):
        """Test posting multiple objects at once."""
        data = [
            {"title": "test1", "artist": {"artist_id": 1}},
            {"album_id": 9999, "title": "test2", "artist": {"artist_id": 1}}
        ]
        resource = AlbumResource(session=self.db_session)
        resource.post_collection(data)
        result1 = self.db_session.query(Album).filter(
            Album.album_id == 9999).first()
        self.assertTrue(result1 is not None)
        result2 = self.db_session.query(Album).filter(
            Album.title == "test2"
        )
        self.assertTrue(result2 is not None)

    def test_post_collection_bad_input(self):
        """Test posting a non list to a collection fails."""
        data = {"title": "test1", "artist_id": 1}
        resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_collection_input",
            resource.post_collection,
            data
        )

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

    # PUT TESTS

    def test_put_validation_fail(self):
        """Test put validation error failure."""
        resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            UnprocessableEntityError,
            "validation_failure",
            resource.put,
            1,
            {"album_id": "bad"}
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

    # DELETE TESTS

    def test_delete(self):
        """Test a simple delete action."""
        resource = AlbumResource(session=self.db_session)
        resource.delete(1)
        result = self.db_session.query(Album).filter(
            Album.album_id == 1
        ).first()
        self.assertTrue(result is None)

    def test_delete_resource_not_found(self):
        """Test deleting a non existant resource fails."""
        resource = AlbumResource(session=self.db_session)
        self.assertRaisesCode(
            ResourceNotFoundError,
            "resource_not_found",
            resource.delete,
            9999999
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

