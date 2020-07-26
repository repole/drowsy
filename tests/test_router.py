"""
    drowsy.tests.test_router
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Router tests for Drowsy.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
import json
from pytest import raises
from drowsy.exc import (
    UnprocessableEntityError, MethodNotAllowedError, BadRequestError,
    ResourceNotFoundError)
from drowsy.router import ModelResourceRouter, ResourceRouterABC
from tests.base import DrowsyDatabaseTests
from tests.models import Album, Track
from tests.resources import (AlbumResource, EmployeeResource)


# BASE
def test_router_abc_get():
    """Make sure ResourceRouterABC raises exception on `get`."""
    with raises(NotImplementedError):
        ResourceRouterABC(resource=None).get("/path")


def test_router_abc_post():
    """Make sure ResourceRouterABC raises exception on `post`."""
    with raises(NotImplementedError):
        ResourceRouterABC(resource=None).post("/path", {})


def test_router_abc_patch():
    """Make sure ResourceRouterABC raises exception on `patch`."""
    with raises(NotImplementedError):
        ResourceRouterABC(resource=None).patch("/path", {})


def test_router_abc_put():
    """Make sure ResourceRouterABC raises exception on `put`."""
    with raises(NotImplementedError):
        ResourceRouterABC(resource=None).put("/path", {})


def test_router_abc_delete():
    """Make sure ResourceRouterABC raises exception on `delete`."""
    with raises(NotImplementedError):
        ResourceRouterABC(resource=None).delete("/path")


def test_router_abc_options():
    """Make sure ResourceRouterABC raises exception on `options`."""
    with raises(NotImplementedError):
        ResourceRouterABC(resource=None).options("/path")


class TestDrowsyRouter(DrowsyDatabaseTests):
    """A collection of tests for drowsy routers.

    These are essentially integration tests, since the
    router makes use of nearly ever component included
    in the package.

    """

    @staticmethod
    def test_router_missing_error_message_fail(db_session):
        """Test that failing with a bad error message is handled."""
        router = ModelResourceRouter(session=db_session)
        with raises(AssertionError):
            router.make_error(key="test")

    @staticmethod
    def test_router_dispatch_get(db_session):
        """Test that auto router dispatch to get works."""
        router = ModelResourceRouter(session=db_session)
        result = router.dispatcher(
            method="get",
            path="/albums/1")
        assert result["album_id"] == 1

    @staticmethod
    def test_router_dispatch_post(db_session):
        """Test that auto router dispatch to post works."""
        router = ModelResourceRouter(session=db_session)
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
        assert result["track_id"] == 4000

    @staticmethod
    def test_router_dispatch_put(db_session):
        """Test that auto router dispatch to put works."""
        router = ModelResourceRouter(session=db_session)
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
        assert result["milliseconds"] == 4000000

    @staticmethod
    def test_router_dispatch_patch(db_session):
        """Test that auto router dispatch to patch works."""
        router = ModelResourceRouter(session=db_session)
        data = {
            "milliseconds": 4000000
        }
        result = router.dispatcher(
            method="patch",
            path="/tracks/1",
            data=data
        )
        assert result["milliseconds"] == 4000000

    @staticmethod
    def test_router_dispatch_delete(db_session):
        """Test that auto router dispatch to delete works."""
        router = ModelResourceRouter(session=db_session)
        result = router.dispatcher(
            method="delete",
            path="/tracks/1")
        assert result is None

    @staticmethod
    def test_router_dispatch_options(db_session):
        """Test that auto router dispatch to options works."""
        router = ModelResourceRouter(session=db_session)
        result = router.dispatcher(
            method="options",
            path="/albums/1")
        assert "GET" in result

    @staticmethod
    def test_router_dispatch_bad_method(db_session):
        """Test that auto router dispatch to a bad method fails."""
        router = ModelResourceRouter(session=db_session)
        with raises(MethodNotAllowedError):
            router.dispatcher(
                method="bad",
                path="/albums/1")

    @staticmethod
    def test_router_dispatch_bad_path(db_session):
        """Test that auto router dispatch to a bad path fails."""
        router = ModelResourceRouter(session=db_session)
        with raises(ResourceNotFoundError):
            router.dispatcher(
                method="get",
                path="/1"
            )

    @staticmethod
    def test_router_context_callable(db_session):
        """Test that a callable context works."""
        router = ModelResourceRouter(
            session=db_session, context=lambda: {"test": True})
        assert router.context.get("test")

    @staticmethod
    def test_router_get_path_parts_too_long(db_session):
        """Test a path with a part after an attr fails."""
        resource = AlbumResource(session=db_session)
        router = ModelResourceRouter(
            session=db_session, resource=resource)
        with raises(ResourceNotFoundError):
            router.get(path="/albums/1/album_id/toolong")

    @staticmethod
    def test_router_get_path_after_missing(db_session):
        """Test a path with a part after an unfound instance fails."""
        resource = AlbumResource(session=db_session)
        router = ModelResourceRouter(
            session=db_session, resource=resource)
        with raises(ResourceNotFoundError):
            router.get(path="/albums/9999999/tracks/")

    @staticmethod
    def test_router_get_empty_non_list_child(db_session):
        """Test getting an empty many to one fails."""
        resource = EmployeeResource(session=db_session)
        router = ModelResourceRouter(session=db_session,
                                     resource=resource)
        # note that employee 1 has no manager...
        with raises(ResourceNotFoundError):
            router.get(path="/employees/1/manager")

    @staticmethod
    def test_router_subquery_parse_error(db_session):
        """Test a get with bad subquery params raises an error."""
        query_params = {
            "tracks._subquery_": 5
        }
        resource = AlbumResource(session=db_session)
        router = ModelResourceRouter(session=db_session,
                                     resource=resource)
        with raises(BadRequestError):
            router.get(
                path="/album/1",
                query_params=query_params)

    @staticmethod
    def test_router_subquery_parse_error_ignore(db_session):
        """Test bad subquery params are ignored (non strict)."""
        query_params = {
            "tracks._subquery_": 5
        }
        resource = AlbumResource(session=db_session)
        router = ModelResourceRouter(session=db_session,
                                     resource=resource)
        result = router.get(path="/album/1", query_params=query_params,
                            strict=False)
        assert result.get("album_id") == 1

    @staticmethod
    def test_router_query_filter_parse_error(db_session):
        """Test a get with bad query filters raises an error."""
        resource = AlbumResource(session=db_session)
        query_params = {
            "query": "[}"
        }
        router = ModelResourceRouter(session=db_session,
                                     resource=resource)
        with raises(BadRequestError):
            router.get(
                path="/albums",
                query_params=query_params)

    @staticmethod
    def test_router_query_filter_parse_error_ignore(db_session):
        """Test a get with bad query filters is ignored (non strict)."""
        resource = AlbumResource(session=db_session)
        query_params = {
            "query": "[}"
        }
        router = ModelResourceRouter(session=db_session,
                                     resource=resource)
        result = router.get(path="/albums", query_params=query_params,
                            strict=False)
        assert len(result) == 347

    @staticmethod
    def test_router_generic_fail(db_session):
        """Test router fail method with a generic problem."""
        resource = AlbumResource(session=db_session)
        router = ModelResourceRouter(session=db_session,
                                     resource=resource)
        error = router.make_error("invalid_complex_filters")
        assert isinstance(error, BadRequestError)

    # POST

    @staticmethod
    def test_router_post(db_session):
        """Test that posting a resource via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
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
        assert result["track_id"] == 4000

    @staticmethod
    def test_router_post_fail(db_session):
        """Test posting a bad resource via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
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
        with raises(UnprocessableEntityError):
            router.post(
                path="/tracks",
                data=tracks[0])

    @staticmethod
    def test_router_post_collection(db_session):
        """Test that posting a resource list via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
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
        assert result is None

    @staticmethod
    def test_router_post_collection_fail(db_session):
        """Test posting a bad resource list via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
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
        with raises(UnprocessableEntityError):
            router.post(
                path="/tracks",
                data=tracks)

    @staticmethod
    def test_router_post_attr(db_session):
        """Test that posting a resource attr via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
        result = router.post("/tracks/14/bytes", data=1)
        assert result == 1

    @staticmethod
    def test_router_post_attr_fail(db_session):
        """Test posting a bad resource attr via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
        with raises(UnprocessableEntityError):
            router.post(
                path="/tracks/14/bytes",
                data="BAD")

    @staticmethod
    def test_router_post_ident_fail(db_session):
        """Test posting to an already identified resource fails."""
        router = ModelResourceRouter(session=db_session, context={})
        with raises(MethodNotAllowedError):
            router.post(
                path="/tracks/14",
                data={})

    @staticmethod
    def test_router_subresource_post(db_session):
        """Test that posting a subresource via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
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
        assert len(result) == 11

    @staticmethod
    def test_router_subresource_post_list(db_session):
        """Test that posting a subresource list via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
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
        assert len(result) == 12

    @staticmethod
    def test_router_subresource_post_only_child(db_session):
        """Test posting a subresource only child via router works."""
        router = ModelResourceRouter(session=db_session, context={})
        artist = {"name": "Nick Repole"}
        result = router.post("/albums/1/artist", data=artist)
        assert result["name"] == "Nick Repole"

    @staticmethod
    def test_router_subresource_post_fail(db_session):
        """Test posting a bad subresource via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
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
        with raises(UnprocessableEntityError):
            router.post(
                path="/albums/1/tracks",
                data=tracks[0])

    @staticmethod
    def test_router_subresource_post_list_fail(db_session):
        """Test posting a bad subresource list via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
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
        with raises(UnprocessableEntityError):
            router.post(
                path="/albums/1/tracks",
                data=tracks)

    @staticmethod
    def test_router_subresource_post_ident_fail(db_session):
        """Test posting to an already identified resource fails."""
        router = ModelResourceRouter(session=db_session, context={})
        with raises(MethodNotAllowedError):
            router.post(
                path="/albums/1/tracks/14",
                data={})

    @staticmethod
    def test_router_subresource_post_attr(db_session):
        """Test that posting a subresource attr via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
        result = router.post("/albums/1/tracks/14/bytes", data=1)
        assert result == 1

    @staticmethod
    def test_router_subresource_post_attr_fail(db_session):
        """Test posting a bad subresource attr via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
        with raises(UnprocessableEntityError):
            router.post(
                path="/albums/1/tracks/14/bytes",
                data="BAD")

    # GET
    @staticmethod
    def test_router_get(db_session):
        """Test getting an identified resource works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1", query_params=query_params)
        assert result["album_id"] == 1

    @staticmethod
    def test_router_get_not_found(db_session):
        """Test getting an identified resource fails with bad id."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                path="/albums/1000000",
                query_params=query_params)

    @staticmethod
    def test_router_get_composite(db_session):
        """Test getting a resource with a composite key works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/compositeNode/1/1", query_params=query_params)
        assert result["composite_id"] == 1

    @staticmethod
    def test_router_get_composite_bad_id(db_session):
        """Test too few identifiers on a composite key fails."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                path="/compositeNode/1",
                query_params=query_params)

    @staticmethod
    def test_router_get_attr(db_session):
        """Test getting an identified resource attr works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/title", query_params=query_params)
        assert result == "For Those About To Rock We Salute You"

    @staticmethod
    def test_router_get_attr_not_found(db_session):
        """Test getting a resource attr fails with bad attr name."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                path="/albums/1/dne",
                query_params=query_params)

    @staticmethod
    def test_router_get_attr_extra_part(db_session):
        """Test getting an attr fails with an extra path part."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                path="/albums/1/title/bad",
                query_params=query_params)

    @staticmethod
    def test_router_get_collection_filtered(db_session):
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
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params)
        assert len(result) == 1
        assert result[0]["album_id"] == 5

    @staticmethod
    def test_router_get_resource_collection_ordered(db_session):
        """Test getting an ordered resource collection via a router."""
        query_params = {
            "sort": "-album_id,title"
        }
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params)
        assert len(result) == 347
        assert result[0]["album_id"] == 347

    @staticmethod
    def test_router_get_resource_collection_first_page(db_session):
        """Test getting the first page of a resource collection."""
        query_params = {
            "sort": "album_id",
            "limit": 30
        }
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params)
        assert len(result) == 30
        assert result[0]["album_id"] == 1

    @staticmethod
    def test_router_get_resource_collection_second_page(db_session):
        """Test getting the second page of a resource collection."""
        query_params = {
            "sort": "album_id",
            "limit": 30,
            "page": "2"
        }
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params)
        assert len(result) == 30
        assert result[0]["album_id"] == 31

    @staticmethod
    def test_router_get_resource_collection_bad_page_fail(db_session):
        """Providing a bad page number fails via a router."""
        query_params = {"page": "2"}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(BadRequestError):
            router.get(
                path="/albums",
                query_params=query_params)

    @staticmethod
    def test_router_get_resource_collection_offset(db_session):
        """Providing an offset query_param works via a router."""
        query_params = {"offset": "1"}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params)
        assert result[0]["album_id"] == 2

    @staticmethod
    def test_router_get_resource_collection_offset_fail(db_session):
        """Providing a bad offset query_param fails via a router."""
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(BadRequestError):
            router.get(
                path="/albums",
                query_params=query_params)

    @staticmethod
    def test_router_get_resource_collection_offset_no_strict(db_session):
        """Providing a bad offset query_param ignored via a router."""
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params, strict=False)
        assert result[0]["album_id"] == 1

    @staticmethod
    def test_router_get_resource_collection_limit_fail(db_session):
        """Providing a bad limit query_param fails via a router."""
        query_params = {"limit": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(BadRequestError):
            router.get(
                path="/albums",
                query_params=query_params)

    @staticmethod
    def test_router_get_resource_collection_limit_no_strict(db_session):
        """Providing a bad limit query_param ignored via a router."""
        query_params = {"limit": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums", query_params=query_params, strict=False)
        assert result[0]["album_id"] == 1

    @staticmethod
    def test_router_get_subresource(db_session):
        """Test getting an identified subresource works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks/14", query_params=query_params)
        assert result["track_id"] == 14

    @staticmethod
    def test_router_get_subresource_only_child(db_session):
        """Test getting an only child subresource works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/artist", query_params=query_params)
        assert result["artist_id"] == 1

    @staticmethod
    def test_router_get_subresource_only_child_not_found(db_session):
        """Test getting only child subresource fails when not found."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                "/employees/1/parent",
                query_params=query_params)

    @staticmethod
    def test_router_get_subresource_not_found(db_session):
        """Test getting an identified subresource fails with bad id."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                path="/albums/1/tracks/1000000",
                query_params=query_params)

    @staticmethod
    def test_router_get_subresource_attr(db_session):
        """Test getting an identified subresource attr works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks/14/name",
                            query_params=query_params)
        assert result == "Spellbound"

    @staticmethod
    def test_router_get_subresource_attr_not_found(db_session):
        """Test getting a subresource attr fails with bad attr name."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.get(
                path="/albums/1/tracks/14/dne",
                query_params=query_params)

    @staticmethod
    def test_router_get_subresource_collection_filtered(db_session):
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
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        assert len(result) == 1
        assert result[0]["track_id"] == 6

    @staticmethod
    def test_router_get_subresource_collection_ordered(db_session):
        """Test getting an ordered subresource collection via router."""
        query_params = {
            "sort": "-track_id,name"
        }
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        assert len(result) == 10
        assert result[0]["track_id"] == 14

    @staticmethod
    def test_router_get_subresource_collection_first_page(db_session):
        """Test getting the first page of a subresource collection."""
        query_params = {
            "sort": "track_id",
            "limit": 5
        }
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        assert len(result) == 5
        assert result[0]["track_id"] == 1

    @staticmethod
    def test_router_get_subresource_collection_second_page(db_session):
        """Test getting the second page of a subresource collection."""
        query_params = {
            "sort": "track_id",
            "limit": 5,
            "page": "2"
        }
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        assert len(result) == 5
        assert result[0]["track_id"] == 10

    @staticmethod
    def test_router_get_subresource_collection_bad_page_fail(db_session):
        """Providing a bad subresource page fails via a router."""
        query_params = {"page": "2"}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(BadRequestError):
            router.get(
                path="/albums/1/tracks",
                query_params=query_params)

    @staticmethod
    def test_router_get_subresource_collection_offset(db_session):
        """Providing an offset subresource query_param works."""
        query_params = {"offset": "1"}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params)
        assert result[0]["track_id"] == 6

    @staticmethod
    def test_router_get_subresource_collection_offset_fail(db_session):
        """Providing a bad offset subresource query_param fails."""
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(BadRequestError):
            router.get(
                path="/albums/1/tracks",
                query_params=query_params)

    @staticmethod
    def test_router_get_subresource_collection_offset_no_strict(db_session):
        """Providing a bad offset subresource query_param ignored."""
        query_params = {"offset": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.get("/albums/1/tracks", query_params=query_params,
                            strict=False)
        assert result[0]["track_id"] == 1

    @staticmethod
    def test_router_get_subresource_collection_limit_fail(db_session):
        """Providing a bad limit subresource query_param fails."""
        query_params = {"limit": "test"}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(BadRequestError):
            router.get(
                path="/albums/1/tracks",
                query_params=query_params)

    # PUT
    @staticmethod
    def test_router_put(db_session):
        """Test that putting a resource via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
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
        assert result["milliseconds"] == 4000000

    @staticmethod
    def test_router_put_attr(db_session):
        """Test that putting a resource attr via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
        result = router.put("/tracks/14/bytes", data=1)
        assert result == 1

    @staticmethod
    def test_router_put_collection(db_session):
        """Test putting a resource collection via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
        with raises(MethodNotAllowedError):
            router.put(
                "/albums",
                data=[])

    @staticmethod
    def test_router_child_put_collection(db_session):
        """Test putting a child collection via a router fails."""
        router = ModelResourceRouter(session=db_session, context={})
        with raises(MethodNotAllowedError):
            router.put(
                "/albums/1/tracks",
                data=[])

    # PATCH
    @staticmethod
    def test_router_patch_attr(db_session):
        """Test that patching a resource attr via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
        result = router.patch("/tracks/14/bytes", data=1)
        assert result == 1

    @staticmethod
    def test_router_patch_object(db_session):
        """Test patching a single child instance works."""
        router = ModelResourceRouter(session=db_session, context={})
        data = {
            "artist_id": 1
        }
        result = router.patch(
            "albums/1/artist",
            data=data
        )
        assert result["artist_id"] == 1

    @staticmethod
    def test_router_patch_object_fails(db_session):
        """Test patching a single child instance with bad data fails."""
        router = ModelResourceRouter(session=db_session, context={})
        data = {
            "artist_id": 1,
            "name": 5
        }
        with raises(UnprocessableEntityError):
            router.patch(
                "albums/1/artist",
                data=data)

    @staticmethod
    def test_router_patch(db_session):
        """Test that patching a resource via a router works."""
        router = ModelResourceRouter(session=db_session, context={})
        track = {
            "milliseconds": 4000000,
            "track_id": 1
        }
        result = router.patch("/tracks/1", data=track)
        assert result["milliseconds"] == 4000000

    @staticmethod
    def test_router_patch_collection(db_session):
        """Test that patching a resource collection via router works."""
        router = ModelResourceRouter(session=db_session, context={})
        tracks = [{
            "milliseconds": 4000000,
            "track_id": 1
        }]
        result = router.patch("/tracks", data=tracks)
        assert result is None

    # DELETE

    @staticmethod
    def test_router_delete(db_session):
        """Test deleting an identified resource works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.delete("/tracks/5", query_params=query_params)
        assert result is None
        track = db_session.query(Track).filter(
            Track.track_id == 5).first()
        assert track is None
        track = db_session.query(Track).filter(
            Track.track_id == 1).first()
        assert track is not None

    @staticmethod
    def test_router_delete_attr(db_session):
        """Test deleting an identified resource attr works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.delete("/customer/1/address", query_params=query_params)
        assert result is None

    @staticmethod
    def test_router_delete_attr_unprocessable(db_session):
        """Test deleting a non null identified resource attr fails."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(UnprocessableEntityError):
            router.delete(
                "/album/1/title",
                query_params=query_params)

    @staticmethod
    def test_router_delete_attr_not_found(db_session):
        """Test deleting an unfindable identified resource attr fails."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        with raises(ResourceNotFoundError):
            router.delete(
                "/album/1/test",
                query_params=query_params)

    @staticmethod
    def test_router_delete_subresource_list(db_session):
        """Test deleting a subresource list works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.delete("albums/1/tracks", query_params=query_params)
        assert result is None
        album = db_session.query(Album).filter(
            Album.album_id == 1
        ).first()
        assert len(album.tracks) == 0

    @staticmethod
    def test_router_delete_subresource_child(db_session):
        """Test deleting a child subresource works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.delete(
            "/tracks/1/genre",
            query_params=query_params)
        assert result is None
        track = db_session.query(Track).filter(
            Track.track_id == 1).first()
        assert track.genre is None

    @staticmethod
    def test_router_delete_collection(db_session):
        """Test deleting a resource collection works."""
        query_params = {}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.delete("/invoices", query_params=query_params)
        assert result is None

    @staticmethod
    def test_router_delete_collection_filtered(db_session):
        """Test deleting a resource collection works with filters."""
        query_params = {"track_id": "5"}
        router = ModelResourceRouter(session=db_session, context={})
        result = router.delete("/tracks", query_params=query_params)
        assert result is None
        track = db_session.query(Track).filter(
            Track.track_id == 5).first()
        assert track is None
        track = db_session.query(Track).filter(
            Track.track_id == 1).first()
        assert track is not None
