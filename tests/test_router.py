"""
    drowsy.tests.test_router
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Router tests for Drowsy.

    :copyright: (c) 2016-2019 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import json
from drowsy.tests.resources import (
    AlbumResource, TrackResource, EmployeeResource)
from drowsy.exc import (
    UnprocessableEntityError, MethodNotAllowedError, BadRequestError,
    ResourceNotFoundError)
from drowsy.router import ModelResourceRouter, ResourceRouterABC
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import Album, Track


class DrowsyRouterTests(DrowsyTests):
    """A collection of tests for drowsy routers.

    These are essentially integration tests, since the
    router makes use of nearly ever component included
    in the package.

    """

    # BASE
    def test_router_abc_get(self):
        """Make sure ResourceRouterABC raises exception on `get`."""
        self.assertRaises(
            NotImplementedError,
            ResourceRouterABC(resource=None).get,
            "/path"
        )

    def test_router_abc_post(self):
        """Make sure ResourceRouterABC raises exception on `post`."""
        self.assertRaises(
            NotImplementedError,
            ResourceRouterABC(resource=None).post,
            "/path",
            {}
        )

    def test_router_abc_patch(self):
        """Make sure ResourceRouterABC raises exception on `patch`."""
        self.assertRaises(
            NotImplementedError,
            ResourceRouterABC(resource=None).patch,
            "/path",
            {}
        )

    def test_router_abc_put(self):
        """Make sure ResourceRouterABC raises exception on `put`."""
        self.assertRaises(
            NotImplementedError,
            ResourceRouterABC(resource=None).put,
            "/path",
            {}
        )

    def test_router_abc_delete(self):
        """Make sure ResourceRouterABC raises exception on `delete`."""
        self.assertRaises(
            NotImplementedError,
            ResourceRouterABC(resource=None).delete,
            "/path"
        )

    def test_router_abc_options(self):
        """Make sure ResourceRouterABC raises exception on `options`."""
        self.assertRaises(
            NotImplementedError,
            ResourceRouterABC(resource=None).options,
            "/path"
        )

    def test_router_missing_error_message_fail(self):
        """Test that failing with a bad error message is handled."""
        router = ModelResourceRouter(session=self.db_session)
        self.assertRaises(
            AssertionError,
            router.make_error,
            key="test"
        )

    def test_router_dispatch_get(self):
        """Test that auto router dispatch to get works."""
        router = ModelResourceRouter(session=self.db_session)
        result = router.dispatcher(
            method="get",
            path="/albums/1")
        self.assertTrue(result["album_id"] == 1)

    def test_router_dispatch_post(self):
        """Test that auto router dispatch to post works."""
        router = ModelResourceRouter(session=self.db_session)
        data = {
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
        result = router.dispatcher(
            method="post",
            path="/tracks",
            data=data
        )
        self.assertTrue(
            result["track_id"] == 4000
        )

    def test_router_dispatch_put(self):
        """Test that auto router dispatch to put works."""
        router = ModelResourceRouter(session=self.db_session)
        data = {
            "album": "/tracks/1/album",
            "bytes": 11170334,
            "composer": "Angus Young, Malcolm Young, Brian Johnson",
            "genre": {"genre_id": 1},
            "media_type": {"media_type_id": 1},
            "milliseconds": 4000000,
            "name": "For Those About To Rock (We Salute You)",
            "playlists": "/tracks/1/playlists",
            "self": "/tracks/1",
            "track_id": 1,
            "unit_price": 0.99
        }
        result = router.dispatcher(
            method="put",
            path="/tracks/1",
            data=data
        )
        self.assertTrue(
            result["milliseconds"] == 4000000
        )

    def test_router_dispatch_patch(self):
        """Test that auto router dispatch to patch works."""
        router = ModelResourceRouter(session=self.db_session)
        data = {
            "milliseconds": 4000000
        }
        result = router.dispatcher(
            method="patch",
            path="/tracks/1",
            data=data
        )
        self.assertTrue(
            result["milliseconds"] == 4000000
        )

    def test_router_dispatch_delete(self):
        """Test that auto router dispatch to delete works."""
        router = ModelResourceRouter(session=self.db_session)
        result = router.dispatcher(
            method="delete",
            path="/tracks/1"
        )
        self.assertTrue(result is None)

    def test_router_dispatch_options(self):
        """Test that auto router dispatch to options works."""
        router = ModelResourceRouter(session=self.db_session)
        result = router.dispatcher(
            method="options",
            path="/albums/1")
        self.assertTrue("GET" in result)

    def test_router_dispatch_bad_method(self):
        """Test that auto router dispatch to a bad method fails."""
        router = ModelResourceRouter(session=self.db_session)
        self.assertRaises(
            MethodNotAllowedError,
            router.dispatcher,
            method="bad",
            path="/albums/1"
        )

    def test_router_dispatch_bad_path(self):
        """Test that auto router dispatch to a bad path fails."""
        router = ModelResourceRouter(session=self.db_session)
        self.assertRaises(
            ResourceNotFoundError,
            router.dispatcher,
            method="get",
            path="/1"
        )

    def test_router_context_callable(self):
        """Test that a callable context works."""
        router = ModelResourceRouter(
            session=self.db_session, context=lambda: {"test": True})
        self.assertTrue(router.context.get("test"))

    def test_router_get_path_parts_too_long(self):
        """Test a path with a part after an attr fails."""
        resource = AlbumResource(session=self.db_session)
        router = ModelResourceRouter(
            session=self.db_session, resource=resource)
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/1/album_id/toolong"
        )

    def test_router_get_path_after_missing(self):
        """Test a path with a part after an unfound instance fails."""
        resource = AlbumResource(session=self.db_session)
        router = ModelResourceRouter(
            session=self.db_session, resource=resource)
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/9999999/tracks/"
        )

    def test_router_get_empty_non_list_child(self):
        """Test getting an empty many to one fails."""
        resource = EmployeeResource(session=self.db_session)
        router = ModelResourceRouter(session=self.db_session,
                                     resource=resource)
        # note that employee 1 has no manager...
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/employees/1/manager"
        )

    def test_router_subquery_parse_error(self):
        """Test a get with bad subquery params raises an error."""
        query_params = {
            "tracks._subquery_": 5
        }
        resource = AlbumResource(session=self.db_session)
        router = ModelResourceRouter(session=self.db_session,
                                     resource=resource)
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/album/1",
            query_params=query_params
        )

    def test_router_subquery_parse_error_ignore(self):
        """Test bad subquery params are ignored (non strict)."""
        query_params = {
            "tracks._subquery_": 5
        }
        resource = AlbumResource(session=self.db_session)
        router = ModelResourceRouter(session=self.db_session,
                                     resource=resource)
        result = router.get(path="/album/1", query_params=query_params,
                            strict=False)
        self.assertTrue(result.get("album_id") == 1)

    def test_router_query_filter_parse_error(self):
        """Test a get with bad query filters raises an error."""
        resource = AlbumResource(session=self.db_session)
        query_params = {
            "query": "[}"
        }
        router = ModelResourceRouter(session=self.db_session,
                                     resource=resource)
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums",
            query_params=query_params
        )

    def test_router_query_filter_parse_error_ignore(self):
        """Test a get with bad query filters is ignored (non strict)."""
        resource = AlbumResource(session=self.db_session)
        query_params = {
            "query": "[}"
        }
        router = ModelResourceRouter(session=self.db_session,
                                     resource=resource)
        result = router.get(path="/albums", query_params=query_params,
                            strict=False)
        self.assertTrue(len(result) == 347)

    def test_router_generic_fail(self):
        """Test router fail method with a generic problem."""
        resource = AlbumResource(session=self.db_session)
        router = ModelResourceRouter(session=self.db_session,
                                     resource=resource)
        error = router.make_error("invalid_complex_filters")
        self.assertTrue(isinstance(error, BadRequestError))

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

    def test_router_get_composite(self):
        """Test getting a resource with a composite key works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/compositeNode/1/1", query_params=query_params)
        self.assertTrue(
            result["composite_id"] == 1
        )

    def test_router_get_composite_bad_id(self):
        """Test too few identifiers on a composite key fails."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/compositeNode/1",
            query_params=query_params
        )

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

    def test_router_get_attr_extra_part(self):
        """Test getting an attr fails with an extra path part."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            path="/albums/1/title/bad",
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
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums",
            query_params=query_params)

    def test_router_get_resource_collection_offset_no_strict(self):
        """Providing a bad offset query_param ignored via a router."""
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums", query_params=query_params, strict=False)
        self.assertTrue(result[0]["album_id"] == 1)

    def test_router_get_resource_collection_limit_fail(self):
        """Providing a bad limit query_param fails via a router."""
        query_params = {"limit": "test"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums",
            query_params=query_params)

    def test_router_get_resource_collection_limit_no_strict(self):
        """Providing a bad limit query_param ignored via a router."""
        query_params = {"limit": "test"}
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

    def test_router_get_subresource_only_child_not_found(self):
        """Test getting only child subresource fails when not found."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.get,
            "/employees/1/parent",
            query_params=query_params
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
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            BadRequestError,
            router.get,
            path="/albums/1/tracks",
            query_params=query_params)

    def test_router_get_subresource_collection_offset_no_strict(self):
        """Providing a bad offset subresource query_param ignored."""
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params,
                            strict=False)
        self.assertTrue(result[0]["track_id"] == 1)

    def test_router_get_subresource_collection_limit_fail(self):
        """Providing a bad limit subresource query_param fails."""
        query_params = {"limit": "test"}
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
            "genre": {"genre_id": 1},
            "media_type": {"media_type_id": 1},
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

    def test_router_put_attr(self):
        """Test that putting a resource attr via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.put("/tracks/14/bytes", data=1)
        self.assertTrue(result == 1)

    def test_router_put_collection(self):
        """Test putting a resource collection via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            MethodNotAllowedError,
            router.put,
            "/albums",
            data=[]
        )

    def test_router_child_put_collection(self):
        """Test putting a child collection via a router fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            MethodNotAllowedError,
            router.put,
            "/albums/1/tracks",
            data=[]
        )

    # PATCH
    def test_router_patch_attr(self):
        """Test that patching a resource attr via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.patch("/tracks/14/bytes", data=1)
        self.assertTrue(result == 1)

    def test_router_patch_object(self):
        """Test patching a single child instance works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        data = {
            "artist_id": 1
        }
        result = router.patch(
            "albums/1/artist",
            data=data
        )
        self.assertTrue(result["artist_id"] == 1)

    def test_router_patch_object_fails(self):
        """Test patching a single child instance with bad data fails."""
        router = ModelResourceRouter(session=self.db_session, context={})
        data = {
            "artist_id": 1,
            "name": 5
        }
        self.assertRaises(
            UnprocessableEntityError,
            router.patch,
            "albums/1/artist",
            data=data
        )

    def test_router_patch(self):
        """Test that patching a resource via a router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        track = {
            "milliseconds": 4000000,
            "track_id": 1
        }
        result = router.patch("/tracks/1", data=track)
        self.assertTrue(
            result["milliseconds"] == 4000000
        )

    def test_router_patch_collection(self):
        """Test that patching a resource collection via router works."""
        router = ModelResourceRouter(session=self.db_session, context={})
        tracks = [{
            "milliseconds": 4000000,
            "track_id": 1
        }]
        result = router.patch("/tracks", data=tracks)
        self.assertTrue(result is None)

    # DELETE

    def test_router_delete(self):
        """Test deleting an identified resource works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.delete("/tracks/5", query_params=query_params)
        self.assertTrue(
            result is None
        )
        track = self.db_session.query(Track).filter(
            Track.track_id == 5).first()
        self.assertTrue(track is None)
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).first()
        self.assertTrue(track is not None)

    def test_router_delete_attr(self):
        """Test deleting an identified resource attr works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.delete("/customer/1/address", query_params=query_params)
        self.assertTrue(
            result is None
        )

    def test_router_delete_attr_unprocessable(self):
        """Test deleting a non null identified resource attr fails."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            UnprocessableEntityError,
            router.delete,
            "/album/1/title",
            query_params=query_params
        )

    def test_router_delete_attr_not_found(self):
        """Test deleting an unfindable identified resource attr fails."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        self.assertRaises(
            ResourceNotFoundError,
            router.delete,
            "/album/1/test",
            query_params=query_params
        )

    def test_router_delete_subresource_list(self):
        """Test deleting a subresource list works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.delete("albums/1/tracks", query_params=query_params)
        self.assertTrue(result is None)
        album = self.db_session.query(Album).filter(
            Album.album_id == 1
        ).first()
        self.assertTrue(len(album.tracks) == 0)

    def test_router_delete_subresource_child(self):
        """Test deleting a child subresource works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.delete(
            "/tracks/1/genre",
            query_params=query_params)
        self.assertTrue(
            result is None
        )
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).first()
        self.assertTrue(
            track.genre is None
        )

    def test_router_delete_collection(self):
        """Test deleting a resource collection works."""
        query_params = {}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.delete("/tracks", query_params=query_params)
        self.assertTrue(
            result is None
        )

    def test_router_delete_collection_filtered(self):
        """Test deleting a resource collection works with filters."""
        query_params = {"track_id": "5"}
        router = ModelResourceRouter(session=self.db_session, context={})
        result = router.delete("/tracks", query_params=query_params)
        self.assertTrue(
            result is None
        )
        track = self.db_session.query(Track).filter(
            Track.track_id == 5).first()
        self.assertTrue(track is None)
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).first()
        self.assertTrue(track is not None)
