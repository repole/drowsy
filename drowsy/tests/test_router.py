"""
    drowsy.tests.test_router
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Router tests for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
import json
from drowsy.exc import (
    UnprocessableEntityError, MethodNotAllowedError, BadRequestError,
    ResourceNotFoundError)
from drowsy.router import ModelResourceRouter
from drowsy.tests.base import DrowsyTests


class DrowsyRouterTests(DrowsyTests):
    """A collection of tests for drowsy routers.

    These are essentially integration tests, since the
    router makes use of nearly ever component included
    in the package.

    """

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
