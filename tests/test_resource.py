"""
    tests.test_resource
    ~~~~~~~~~~~~~~~~~~~

    Resource tests for Drowsy.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from marshmallow.exceptions import RegistryError
import drowsy.resource_class_registry as registry
from drowsy.base import ResourceABC, NestableResourceABC, SchemaResourceABC
from drowsy.exc import (
    BadRequestError, MethodNotAllowedError, PermissionDeniedError,
    ResourceNotFoundError, UnprocessableEntityError)
from drowsy.parser import SubfilterInfo, SortInfo
from drowsy.resource import ResourceCollection, PaginationInfo
from tests.base import DrowsyDatabaseTests
from tests.models import Album, Artist, Playlist, Track
from tests.resources import (
    AlbumResource, AlbumCamelResource, ArtistResource, CompositeNodeResource,
    CompositeOneResource, CustomerResource, EmployeeResource, InvoiceResource,
    InvoiceCamelResource, PlaylistResource, TrackResource)
from pytest import raises
from unittest.mock import MagicMock
from sqlalchemy.orm.session import Session


# ABSTRACT CLASS TESTS

def test_resource_abc_get():
    """Make sure ResourceABC raises exception on `get`."""
    with raises(NotImplementedError):
        ResourceABC().get(1)


def test_resource_abc_post():
    """Make sure ResourceABC raises exception on `post`."""
    with raises(NotImplementedError):
        ResourceABC().post({})


def test_resource_abc_patch():
    """Make sure ResourceABC raises exception on `patch`."""
    with raises(NotImplementedError):
        ResourceABC().patch(1, {})


def test_resource_abc_put():
    """Make sure ResourceABC raises exception on `put`."""
    with raises(NotImplementedError):
        ResourceABC().put(1, {})


def test_resource_abc_delete():
    """Make sure ResourceABC raises exception on `delete`."""
    with raises(NotImplementedError):
        ResourceABC().delete(1)


def test_resource_abc_get_collection():
    """Check ResourceABC raises exception on `get_collection`."""
    with raises(NotImplementedError):
        ResourceABC().get_collection()


def test_resource_abc_post_collection():
    """Check ResourceABC raises exception on `post_collection`."""
    with raises(NotImplementedError):
        ResourceABC().post_collection({})


def test_resource_abc_patch_collection():
    """Check ResourceABC raises exception on `patch_collection`."""
    with raises(NotImplementedError):
        ResourceABC().patch_collection({})


def test_resource_abc_put_collection():
    """Check ResourceABC raises exception on `put_collection`."""
    with raises(NotImplementedError):
        ResourceABC().put_collection({})


def test_resource_abc_delete_collection():
    """Check ResourceABC raises exception on `delete_collection`."""
    with raises(NotImplementedError):
        ResourceABC().delete_collection()


def test_resource_abc_options():
    """Make sure ResourceABC raises exception on `options`."""
    with raises(NotImplementedError):
        getattr(ResourceABC(), "options")


def test_nestable_resource_abc_make_resource():
    """NestableResourceABC exception on `make_subresource`."""
    with raises(NotImplementedError):
        NestableResourceABC().make_subresource("test")


def test_schema_resource_abc_make_resource():
    """SchemaResourceABC raises exception on `make_schema`."""
    with raises(NotImplementedError):
        SchemaResourceABC().make_schema()


def test_schema_resource_abc_schema_kwargs():
    """SchemaResourceABC raises exception on `get_schema_kwargs`."""
    with raises(NotImplementedError):
        getattr(SchemaResourceABC(), "_get_schema_kwargs")("test")


def test_schema_resource_abc_schema():
    """SchemaResourceABC raises exception on `session`."""
    with raises(NotImplementedError):
        getattr(SchemaResourceABC(), "schema")


def test_schema_resource_abc_context():
    """SchemaResourceABC raises exception on `context`."""
    with raises(NotImplementedError):
        getattr(SchemaResourceABC(), "context")


# REGISTRY TESTS
def test_registry_find_class():
    """Test the registry finds a class."""
    assert (
        registry.get_class("AlbumResource", all=True) == AlbumResource)


def test_registry_duplicate_class():
    """Test that multiple registrations under the same name work."""
    registry.register("AlbumResource", dict)
    with raises(RegistryError):
        registry.get_class("AlbumResource", all=False)
    assert (
        len(registry.get_class("AlbumResource", all=True)) == 2)
    # clean up the mess we just made in the registry
    registry._registry["AlbumResource"].remove(dict)


def test_registry_class_not_found():
    """Test the registry acts as expected when no class is found."""
    with raises(RegistryError):
        registry.get_class("Test", all=False)


# PAGINATION TESTS
def test_pagination_info_current_page():
    """Test PaginationInfo current_page works with positive int."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=4
    )
    assert info.current_page == 4


def test_pagination_info_current_page_none():
    """Test PaginationInfo current_page works with a None value."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=None
    )
    assert info.current_page is None


def test_pagination_info_current_page_negative():
    """Test PaginationInfo current_page fails with negative int."""
    with raises(ValueError):
        PaginationInfo(
            resources_available=100,
            page_size=10,
            current_page=-4
        )


def test_pagination_info_current_page_non_int():
    """Test PaginationInfo current_page fails with non int."""
    with raises(TypeError):
        PaginationInfo(
            resources_available=100,
            page_size=10,
            current_page="1"
        )


def test_pagination_info_page_size():
    """Test PaginationInfo page_size works with positive int."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=4
    )
    assert info.page_size == 10


def test_pagination_info_page_size_none():
    """Test PaginationInfo page_size works with a None value."""
    info = PaginationInfo(
        resources_available=100,
        page_size=None,
        current_page=None
    )
    assert info.page_size is None


def test_pagination_info_page_size_negative():
    """Test PaginationInfo page_size fails with negative int."""
    with raises(ValueError):
        PaginationInfo(
            resources_available=100,
            page_size=-10,
            current_page=1
        )


def test_pagination_info_page_size_non_int():
    """Test PaginationInfo page_size fails with non int."""
    with raises(TypeError):
        PaginationInfo(
            resources_available=100,
            page_size="10",
            current_page=1
        )


def test_pagination_info_first_page():
    """Test PaginationInfo first_page works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=4
    )
    assert info.first_page == 1


def test_pagination_info_first_page_none():
    """Test PaginationInfo first_page as None works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=None,
        current_page=None
    )
    assert info.first_page is None


def test_pagination_info_last_page():
    """Test PaginationInfo last_page works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=4
    )
    assert info.last_page == 10


def test_pagination_info_last_page_none():
    """Test PaginationInfo last_page as None works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=None,
        current_page=None
    )
    assert info.last_page is None


def test_pagination_info_next_page():
    """Test PaginationInfo next_page works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=4
    )
    assert info.next_page == 5


def test_pagination_info_next_page_none():
    """Test PaginationInfo next_page as None works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=None,
        current_page=None
    )
    assert info.next_page is None


def test_pagination_info_next_page_not_found():
    """Test PaginationInfo next_page when on last page works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=10
    )
    assert info.next_page is None


def test_pagination_info_previous_page():
    """Test PaginationInfo previous_page works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=4
    )
    assert info.previous_page == 3


def test_pagination_info_previous_page_none():
    """Test PaginationInfo previous_page as None works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=None,
        current_page=None
    )
    assert info.previous_page is None


def test_pagination_info_previous_page_not_found():
    """Test PaginationInfo previous_page from first page works."""
    info = PaginationInfo(
        resources_available=100,
        page_size=10,
        current_page=1
    )
    assert info.previous_page is None


# RESOURCECOLLECTION TESTS

def test_resource_collection_class():
    """Test the ResourceCollection class."""
    rc = ResourceCollection([1, 2, 3], 100)
    assert rc[0] == 1
    assert rc.resources_fetched == 3
    assert rc.resources_available == 100


class TestDrowsyResource(DrowsyDatabaseTests):

    """Test drowsy resources."""

    # RESOURCE CLASS TESTS

    @staticmethod
    def test_resource_session_callable(db_session):
        """Test that providing a callable session works."""
        def session_callable():
            """Dummy session callable."""
            return db_session
        resource = EmployeeResource(session=session_callable)
        assert resource.session is db_session

    @staticmethod
    def test_resource_session_setter(db_session):
        """Test setting a session works."""
        resource = EmployeeResource(session=db_session)
        new_session = MagicMock(spec=Session)
        resource.session = new_session
        assert resource.session is not db_session
        # For some reason it seems like the MagicMock is changing here
        # TODO - Research this
        assert resource.session is not None

    @staticmethod
    def test_resource_context_callable(db_session):
        """Test that providing a callable context works."""
        def context_callable():
            """Dummy context callable."""
            return {"test": "test"}
        resource = EmployeeResource(session=db_session,
                                    context=context_callable)
        assert resource.context.get("test") == "test"

    @staticmethod
    def test_resource_context_setter(db_session):
        """Test setting a resource context works."""
        resource = EmployeeResource(session=db_session,
                                    context={})
        resource.context = {"test": "test"}
        assert resource.context.get("test") == "test"

    @staticmethod
    def test_resource_page_max_size(db_session):
        """Test that providing a page_max_size works."""
        resource = EmployeeResource(session=db_session,
                                    page_max_size=100)
        assert resource.page_max_size == 100

    @staticmethod
    def test_resource_page_max_size_0(db_session):
        """Test that providing 0 for page_max_size works."""
        resource = EmployeeResource(session=db_session,
                                    page_max_size=0)
        assert resource.page_max_size is None

    @staticmethod
    def test_resource_limit_too_high_fail(db_session):
        """Test providing a limit greater than page_max_size fails."""
        resource = EmployeeResource(session=db_session,
                                    page_max_size=100)
        with raises(BadRequestError) as excinf:
            resource.get_collection(
                limit=101,
                strict=True
            )
        assert excinf.value.code == "limit_too_high"

    @staticmethod
    def test_resource_limit_negative_fail(db_session):
        """Test providing a negative_limit fails."""
        resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            resource.get_collection(
                limit=-1,
                strict=True
            )
        assert excinf.value.code == "invalid_limit_value"

    @staticmethod
    def test_resource_limit_too_high_soft_fail(db_session):
        """Test in non strict page_max_size overrides high limit."""
        resource = AlbumResource(session=db_session,
                                 page_max_size=100)
        results = resource.get_collection(
            limit=101,
            strict=False)
        assert len(results) == 100

    @staticmethod
    def test_resource_offset_negative_fail(db_session):
        """Test providing a negative_limit fails."""
        resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            resource.get_collection(
                offset=-1,
                strict=True
            )
        assert excinf.value.code == "invalid_offset_value"

    @staticmethod
    def test_resource_error_message_override(db_session):
        """Test that error message overrides are handled properly."""
        resource = EmployeeResource(session=db_session)
        with raises(BadRequestError) as excinf:
            raise resource.make_error(key="invalid_field")
        assert excinf.value.code == "invalid_field"
        assert excinf.value.message == "Test invalid_field message."

    @staticmethod
    def test_resource_make_subresource_fail(db_session):
        """Test that attempting to make an invalid subresource fails."""
        resource = EmployeeResource(session=db_session,
                                    page_max_size=0)
        with raises(ValueError):
            resource.make_subresource("test")

    @staticmethod
    def test_resource_fail_missing_key(db_session):
        """Test resource failure missing key error message."""
        resource = EmployeeResource(session=db_session)
        with raises(AssertionError):
            resource.make_error(key="test")

    @staticmethod
    def test_resource_fail_invalid_filters(db_session):
        """Test resource failure with invalid_filters and no exc."""
        resource = EmployeeResource(session=db_session)
        error = resource.make_error("invalid_filters")
        assert isinstance(error, BadRequestError)

    @staticmethod
    def test_resource_whitelist(db_session):
        """Test that a multi level whitelist check works."""
        resource = AlbumResource(session=db_session)
        assert resource.whitelist("tracks.playlists.playlist_id")

    @staticmethod
    def test_resource_whitelist_empty(db_session):
        """Test whitelist with an empty string returns True."""
        resource = AlbumResource(session=db_session)
        assert resource.whitelist("")

    @staticmethod
    def test_resource_whitelist_non_nested_resource(db_session):
        """Test whitelist using a nested field without a resource."""
        resource = InvoiceResource(session=db_session)
        assert resource.whitelist("invoice_lines.unit_price")

    @staticmethod
    def test_resource_whitelist_fail(db_session):
        """Test that a single level whitelist check properly fails."""
        resource = CustomerResource(session=db_session)
        assert resource.whitelist("phone") is False

    @staticmethod
    def test_resource_whitelist_nested_fail(db_session):
        """Test that a multi level whitelist check properly fails."""
        resource = EmployeeResource(session=db_session)
        assert resource.whitelist("parent.customers.phone") is False

    @staticmethod
    def test_resource_whitelist_bad_key_fail(db_session):
        """Test bad attribute names properly fail whitelist check."""
        resource = CustomerResource(session=db_session)
        assert resource.whitelist("test") is False

    @staticmethod
    def test_resource_convert_non_nested_resource(db_session):
        """Test converting using a nested field without a resource."""
        resource = InvoiceCamelResource(session=db_session)
        assert (
            "invoice_lines.unit_price" == resource.convert_key_name(
                "invoiceLines.unitPrice"))

    @staticmethod
    def test_resource_convert_bad_key_fail(db_session):
        """Test converting with a bad nested key."""
        resource = AlbumCamelResource(session=db_session)
        assert resource.convert_key_name("albumId.test") is None

    @staticmethod
    def test_resource_make_schema_embeds_subfilters(db_session):
        """Test supplying conflicting embeds and subfilters works."""
        resource = AlbumResource(session=db_session)
        result = resource.make_schema(
            embeds=["tracks.track_id"],
            subfilters={"tracks": {}}
        )
        assert result.fields["tracks"].embedded

    @staticmethod
    def test_resource_make_schema_embeds_fields(db_session):
        """Test supplying embeds and fields together works."""
        resource = AlbumResource(session=db_session)
        result = resource.make_schema(
            embeds=["tracks.track_id"],
            fields=["album_id"])
        assert result.fields["tracks"].embedded

    @staticmethod
    def test_resource_make_schema_embeds_fail(db_session):
        """Test supplying bad embeds fails."""
        resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            resource.make_schema(embeds=["album"])
        assert excinf.value.code == "invalid_embed"

    @staticmethod
    def test_resource_check_method_allowed(db_session):
        """Test a disallowed method fails."""
        resource = InvoiceResource(session=db_session)
        with raises(MethodNotAllowedError) as excinf:
            resource.get(
                1,
                head=True)
        assert excinf.value.code == "method_not_allowed"


    # PATCH TESTS

    @staticmethod
    def test_patch_simple(db_session):
        """Make sure that a simple obj update works."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        result = album_resource.patch((album.album_id,), {"title": "TEST"})
        assert result["title"] == "TEST"
        assert album.title == "TEST"

    @staticmethod
    def test_patch_no_tuple_ident(db_session):
        """Test passing a single value identity works."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        result = album_resource.patch(album.album_id, {"title": "TEST"})
        assert result["title"] == "TEST"
        assert album.title == "TEST"

    @staticmethod
    def test_patch_bad_ident_fail(db_session):
        """Ensure a bad ident in patch causes failure."""
        album_resource = AlbumResource(session=db_session)
        with raises(ResourceNotFoundError) as excinf:
            album_resource.patch(
                ("TEST", ),
                {}
            )
        print(excinf.value)
        assert excinf.value.code == "resource_not_found"

    @staticmethod
    def test_patch_empty(db_session):
        """Make sure that a obj update works with no update params."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        result = album_resource.patch((album.album_id,), {})
        assert result["title"] == album.title

    @staticmethod
    def test_patch_add_existing_subresource(db_session):
        """Make sure that we can add an item to a list relation."""
        playlist = db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        assert len(playlist.tracks) == 1
        playlist_resource = PlaylistResource(session=db_session)
        update_data = {
            "tracks": [{
                "$op": "add",
                "track_id": "1"
            }]
        }
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        assert len(playlist.tracks) == 2
        assert len(result["tracks"]) == 2

    @staticmethod
    def test_patch_subresource_list_add_new(db_session):
        """Ensure we can add a new obj to a list using relationship."""
        playlist = db_session.query(Playlist).filter(
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
        playlist_resource = PlaylistResource(session=db_session)
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        assert len(playlist.tracks) == 2
        assert len(result["tracks"]) == 2
        assert playlist.tracks[1].composer == "Nick Repole"
        assert result["tracks"][1]["composer"] == "Nick Repole"

    @staticmethod
    def test_patch_subresource_list_update_existing(db_session):
        """Ensure we can update a list relationship item."""
        playlist = db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        playlist_resource = PlaylistResource(session=db_session)
        update_data = {
            "tracks": [{
                "track_id": 597,
                "name": "Test Track Seven"
            }]
        }
        result = playlist_resource.patch((playlist.playlist_id,), update_data)
        assert playlist.tracks[0].name == "Test Track Seven"
        assert result["tracks"][0]["name"] == playlist.tracks[0].name

    @staticmethod
    def test_patch_subresource_single_update_existing(db_session):
        """Make sure that a non-list relation can have a field set."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        update_data = {
            "artist": {"name": "TEST"}
        }
        album_resource = AlbumResource(session=db_session)
        result = album_resource.patch((album.album_id,), update_data)
        assert album.artist.name == "TEST"
        assert result["artist"]["name"] == album.artist.name

    @staticmethod
    def test_patch_permission_denied(db_session):
        """Test patch permission denial."""
        data = {"album_id": 340, "title": "Denied"}
        resource = AlbumResource(session=db_session)
        with raises(PermissionDeniedError):
            resource.patch(340, data)

    @staticmethod
    def test_single_relation_item_set_fail(db_session):
        """Ensure we can't set a relation to a non object value."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError):
            album_resource.patch(
                (album.album_id, ),
                {"artist": 5}
            )

    @staticmethod
    def test_list_relation_set_fail(db_session):
        """Ensure we can't set a list relation to a non object value."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError):
            album_resource.patch(
                (album.album_id, ),
                {"tracks": 5})

    @staticmethod
    def test_list_relation_non_item_fail(db_session):
        """Ensure we can't set list relation items to a non object."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError):
            album_resource.patch(
                (album.album_id, ),
                {"tracks": ["TEST"]})

    @staticmethod
    def test_list_relation_bad_item_value_fail(db_session):
        """Ensure list relation item validation works."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError):
            album_resource.patch(
                (album.album_id, ),
                {"tracks": [{"bytes": "TEST"}]})

    @staticmethod
    def test_set_single_relation_item(db_session):
        """Make sure that a non-list relation can be set."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).all()[0]
        album_resource = AlbumResource(session=db_session)
        update_params = {
            "artist": {"artist_id": 3}
        }
        result = album_resource.patch((album.album_id,), update_params)
        assert album.artist.name == "Aerosmith"
        assert result["artist"]["name"] == album.artist.name

    @staticmethod
    def test_set_single_relation_item_to_none(db_session):
        """Make sure that a non-list relation can be set to ``None``."""
        track = db_session.query(Track).filter(
            Track.track_id == 1).all()[0]
        track_resource = TrackResource(session=db_session)
        update_params = {
            "genre": None
        }
        result = track_resource.patch((track.track_id,), update_params)
        assert track.genre is None
        assert result["genre"] is None

    @staticmethod
    def test_set_empty_single_relation_item(db_session):
        """Make sure that an empty non-list relation can be set."""
        track = db_session.query(Track).filter(
            Track.track_id == 1).all()[0]
        track.genre = None
        db_session.commit()
        track_resource = TrackResource(session=db_session)
        update_data = {
            "genre": {"genre_id": 1}
        }
        result = track_resource.patch((track.track_id, ), update_data)
        assert track.genre.name == "Rock"
        assert result["genre"]["name"] == track.genre.name

    @staticmethod
    def test_list_relation_remove_item(db_session):
        """Make sure that we can remove an item from a list relation."""
        playlist = db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).first()
        playlist_resource = PlaylistResource(session=db_session)
        update_params = {
            "tracks": [{
                "track_id": 597,
                "$op": "remove"
            }]
        }
        result = playlist_resource.patch(
            (playlist.playlist_id, ), update_params)
        assert len(playlist.tracks) == 0
        assert len(result["tracks"]) == 0

    @staticmethod
    def test_new_single_relation_item(db_session):
        """Make sure that a non-list relation can be created."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).first()
        album_resource = AlbumResource(session=db_session)
        update_params = {
            "artist": {
                "artist_id": 999,
                "name": "Nick Repole",
            }
        }
        result = album_resource.patch((album.album_id,), update_params)
        # make sure original artist wasn't just edited.
        artist = db_session.query(Artist).filter(
            Artist.artist_id == 1).first()
        assert album.artist.name == "Nick Repole"
        assert result["artist"]["name"] == album.artist.name
        assert artist is not None

    # GET TESTS

    @staticmethod
    def test_get(db_session):
        """Test simple get functionality."""
        resource = AlbumResource(session=db_session)
        result = resource.get(1)
        assert result["album_id"] == 1

    @staticmethod
    def test_get_with_query(db_session):
        """Test get with a pre-existing query."""
        query = db_session.query(Album).filter(
            Album.title == "test")
        resource = AlbumResource(session=db_session)
        with raises(ResourceNotFoundError) as excinf:
            resource.get(1, session=query)
        assert excinf.value.code == "resource_not_found"

    @staticmethod
    def test_get_bad_ident(db_session):
        """Test get fails with a bad identity provided."""
        resource = AlbumResource(session=db_session)
        with raises(ResourceNotFoundError) as excinf:
            resource.get("bad")
        assert excinf.value.code == "resource_not_found"

    @staticmethod
    def test_get_bad_embed(db_session):
        """Test get fails with a bad embed."""
        resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            resource.get(
                1,
                embeds=["test"],
                strict=True
            )
        assert excinf.value.code == "invalid_embed"

    @staticmethod
    def test_make_schema_invalid_field(db_session):
        """Test making a new schema fails with a bad field."""
        resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            resource.make_schema(
                fields=["test"],
                strict=True
            )
        assert excinf.value.code == "invalid_field"

    # GET COLLECTION TESTS

    @staticmethod
    def test_get_collection(db_session):
        """Test simple get_collection functionality."""
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection()
        assert len(result) == 347

    @staticmethod
    def test_get_collection_filters(db_session):
        """Test simple get_collection filtering functionality."""
        filters = {
            "$and": [
                {"album_id": {"$lt": "10"}},
                {"title": {"$like": "Big"}},
                {"album_id": {"$gt": "4"}},
                {"album_id": {"$gte": "5"}},
                {"album_id": {"$lte": "5"}},
                {"album_id": {"$eq": "5"}},
                {"album_id": 5},
                {"album_id": {"$ne": 6}},
                {"title": "Big Ones"}
            ]
        }
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            filters=filters
        )
        assert len(result) == 1
        assert result[0]["album_id"] == 5

    @staticmethod
    def test_get_collection_invalid_filters(db_session):
        """Test simple get_collection filtering failure."""
        filters = {
            "$and": [
                {"title": {"$bad": "Big Ones"}}
            ]
        }
        album_resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            album_resource.get_collection(filters=filters)
        assert excinf.value.code == "filters_field_op_error"

    @staticmethod
    def test_get_collection_invalid_sorts_type(db_session):
        """Test non list sorts with get_collection fails."""
        album_resource = AlbumResource(session=db_session)
        with raises(TypeError):
            album_resource.get_collection(sorts="test")

    @staticmethod
    def test_get_collection_invalid_sort_type(db_session):
        """Test non SortInfo sort with get_collection fails."""
        album_resource = AlbumResource(session=db_session)
        with raises(TypeError):
            album_resource.get_collection(sorts=["test"])

    @staticmethod
    def test_get_collection_invalid_sort_field(db_session):
        """Test a bad field on SortInfo with get_collection fails."""
        album_resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            album_resource.get_collection(sorts=[SortInfo(attr="TEST")])
        assert excinf.value.code == "invalid_sort_field"

    @staticmethod
    def test_get_collection_subresource_query(db_session):
        """Test a subresource query."""
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            subfilters={"tracks": SubfilterInfo(
                filters={'track_id': 1}
            )}
        )
        for album in result:
            for track in album["tracks"]:
                assert track["track_id"] == 1

    @staticmethod
    def test_get_collection_subresource_fail(db_session):
        """Test a subresource query fails with bad filters."""
        album_resource = AlbumResource(session=db_session)
        with raises(BadRequestError) as excinf:
            album_resource.get_collection(
                subfilters={"tracks": SubfilterInfo(
                    filters={'track_id': {"$bad": 5}}
                )}
            )
        assert excinf.value.code == "filters_field_op_error"

    @staticmethod
    def test_get_collection_simple(db_session):
        """Test getting all objects with an empty dict of params."""
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            filters={}
        )
        assert len(result) == 347

    @staticmethod
    def test_get_collection_empty_filters(db_session):
        """Test getting all objects with empty filters."""
        filters = {"$and": []}
        album_resource = AlbumResource(session=db_session)
        result = album_resource.get_collection(
            filters=filters
        )
        assert len(result) == 347

    @staticmethod
    def test_get_collection_nested_filters(db_session):
        """Test get_collection filtering uses required filters."""
        filters = {"tracks.track_id": 130}
        album_resource = AlbumResource(
            session=db_session
        )
        result = album_resource.get_collection(
            filters=filters
        )
        assert len(result) == 1

    @staticmethod
    def test_get_collection_required_nested_filters(db_session):
        """Test collection filtering uses nested required filters."""
        filters = {"tracks.track_id": 130}
        album_resource = AlbumResource(
            session=db_session,
            context={"user": "limited"}
        )
        result = album_resource.get_collection(
            filters=filters
        )
        assert len(result) == 0

    @staticmethod
    def test_get_collection_required_filters(db_session):
        """Test get_collection filtering uses required filters."""
        filters = {"track_id": 130}
        resource = TrackResource(
            session=db_session,
            context={"user": "limited"}
        )
        result = resource.get_collection(
            filters=filters
        )
        assert len(result) == 0

    @staticmethod
    def test_get_collection_required_single_filter(db_session):
        """Test collection filtering uses single required filter."""
        filters = {"track_id": 130}
        resource = TrackResource(
            session=db_session,
            context={"user": "limited_single_filter"}
        )
        result = resource.get_collection(
            filters=filters
        )
        assert len(result) == 0

    @staticmethod
    def test_get_required_nested_filters_empty_string(db_session):
        """Empty input to `get_required_nested_filters` returns None."""
        resource = AlbumResource(session=db_session)
        assert resource.get_required_nested_filters("") is None

    @staticmethod
    def test_get_required_nested_filters_multilevel(db_session):
        """Ensure multiple levels of nested filters work."""
        resource = ArtistResource(
            session=db_session,
            context={"user": "limited_single_filter"})
        assert resource.get_required_nested_filters("albums.tracks") is not None

    # POST TESTS

    @staticmethod
    def test_post(db_session):
        """Test a simple post."""
        data = {"album_id": 9999, "title": "test2", "artist": {"artist_id": 1}}
        resource = AlbumResource(session=db_session)
        resource.post(data)
        result = db_session.query(Album).filter(
            Album.album_id == 9999).first()
        assert result is not None

    @staticmethod
    def test_post_fail_already_exists(db_session):
        """Test post fails when the same id already exists."""
        resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            resource.post(
                {"album_id": 1, "title": "test2", "artist": {"artist_id": 1}}
            )
        assert excinf.value.code == "validation_failure"

    @staticmethod
    def test_post_permission_denied(db_session):
        """Test post permission denied errors work as expected."""
        resource = AlbumResource(session=db_session)
        data = {
            "album_id": 9999,
            "title": "Denied"
        }
        with raises(PermissionDeniedError):
            resource.post(data)

    @staticmethod
    def test_post_self_ref(db_session):
        """Self referential object creation."""
        resource = EmployeeResource(session=db_session)
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "subordinates": [
                {"employee_id": 2},
                {"employee_id": 3}
            ]
        }
        result = resource.post(data=data)
        assert result is not None
        assert len(result.get("subordinates", [])) == 2
        assert result["subordinates"][0].get("employee_id") == 2
        assert result["subordinates"][1].get("employee_id") == 3

    @staticmethod
    def test_post_fk_as_pk(db_session):
        """Nested object creation where the PK is a FK."""
        resource = TrackResource(session=db_session)
        data = {
            "name": "New TestTrack",
            "album": {
                "album_id": "347",
            },
            "media_type": {
                "media_type_id": 1
            },
            "milliseconds": 1,
            "unit_price": 1.0,
            "track_stats": {
                "downloads": 100
            }
        }
        result = resource.post(data=data)
        assert result is not None
        assert result["track_id"] == result["track_stats"]["track_id"]

    @staticmethod
    def test_post_composite_nested(db_session):
        """Nested object creation with a composite key."""
        resource = CompositeNodeResource(session=db_session)
        data = {
            "node_id": 10,
            "composite_id": 1,
            "children": [
                {
                    "node_id": 11,
                    "composite_id": 1
                }
            ]
        }
        result = resource.post(data=data)
        assert result is not None
        assert result["node_id"] == 10
        assert result["children"][0]["node_id"] == 11

    @staticmethod
    def test_post_composite_nested_one_to_many(db_session):
        """Nested one to many creation with a composite key."""
        resource = CompositeOneResource(session=db_session)
        data = {
            "one_id": 6,
            "composite_one_id": 1,
            "many": [
                {
                    "many_id": 7
                }
            ]
        }
        result = resource.post(data=data)
        assert result is not None
        assert result["one_id"] == 6
        assert result["many"][0]["many_id"] == 7

    # POST COLLECTION TESTS

    @staticmethod
    def test_post_collection(db_session):
        """Test posting multiple objects at once."""
        data = [
            {"title": "test1", "artist": {"artist_id": 1}},
            {"album_id": 9999, "title": "test2", "artist": {"artist_id": 1}}
        ]
        resource = AlbumResource(session=db_session)
        resource.post_collection(data)
        result1 = db_session.query(Album).filter(
            Album.album_id == 9999).first()
        assert result1 is not None
        result2 = db_session.query(Album).filter(
            Album.title == "test2"
        )
        assert result2 is not None

    @staticmethod
    def test_post_collection_bad_input(db_session):
        """Test posting a non list to a collection fails."""
        data = {"title": "test1", "artist_id": 1}
        resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            resource.post_collection(data)
        assert excinf.value.code == "invalid_collection_input"

    @staticmethod
    def test_post_collection_no_relation_fail(db_session):
        """Test a missing non list relation causes a post fail."""
        data = {"title": "test1"}
        resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            resource.post(data)
        assert excinf.value.code == "validation_failure"

    @staticmethod
    def test_post_collection_permission_denied(db_session):
        """Test post collection permission denied errors."""
        resource = AlbumResource(session=db_session)
        data = [{
            "album_id": 9999,
            "title": "Denied"
        }]
        with raises(PermissionDeniedError):
            resource.post_collection(data)

    # PATCH COLLECTION TESTS

    @staticmethod
    def test_patch_collection_add(db_session):
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
        playlist_resource = PlaylistResource(session=db_session)
        result = playlist_resource.patch_collection(update_data)
        playlists = db_session.query(Playlist).filter(
            Playlist.playlist_id == 9999).all()
        assert len(playlists) == 1
        assert len(playlists[0].tracks) == 1
        assert result is None

    @staticmethod
    def test_patch_collection_permission_denied(db_session):
        """Test patch collection permission denial."""
        data = [{"album_id": 340, "title": "Denied"}]
        resource = AlbumResource(session=db_session)
        with raises(PermissionDeniedError):
            resource.patch_collection(data)


    @staticmethod
    def test_patch_collection_set_child(db_session):
        """Test setting a non list relationship via patch works."""
        update_data = [
            {
                "$op": "add",
                "track_id": 9999,
                "name": "New TestTrack",
                "album": {
                    "album_id": "347",
                },
                "media_type": {
                    "media_type_id": 1
                },
                "milliseconds": 1,
                "unit_price": 1.0
            }
        ]
        track_resource = TrackResource(session=db_session)
        result = track_resource.patch_collection(update_data)
        tracks = db_session.query(Track).filter(
            Track.track_id == 9999).all()
        assert len(tracks) == 1
        assert result is None

    @staticmethod
    def test_patch_collection_remove(db_session):
        """Test removing from a collection via patch works."""
        update_data = [
            {
                "$op": "remove",
                "playlist_id": 18
            }
        ]
        playlist_resource = PlaylistResource(session=db_session)
        result = playlist_resource.patch_collection(update_data)
        playlists = db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()
        assert len(playlists) == 0
        assert result is None

    @staticmethod
    def test_patch_collection_update(db_session):
        """Test updating from a collection via patch works."""
        update_data = [
            {
                "playlist_id": 18,
                "name": "New name"
            }
        ]
        playlist_resource = PlaylistResource(session=db_session)
        result = playlist_resource.patch_collection(update_data)
        playlists = db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()
        assert len(playlists) == 1
        assert playlists[0].name == "New name"
        assert result is None

    @staticmethod
    def test_patch_collection_bad_data(db_session):
        """Test providing a non list to patch collection fails."""
        update_data = {
            "playlist_id": 18,
            "name": "New name"
        }
        playlist_resource = PlaylistResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            playlist_resource.patch_collection(update_data)
        assert excinf.value.code == "invalid_collection_input"

    @staticmethod
    def test_patch_collection_update_fail(db_session):
        """Test updating a collection via patch fails validation."""
        update_data = [
            {
                "playlist_id": 18,
                "name": 5
            }
        ]
        playlist_resource = PlaylistResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            playlist_resource.patch_collection(update_data)
        assert excinf.value.code == "validation_failure"

    @staticmethod
    def test_patch_collection_add_fail(db_session):
        """Test adding to a collection via patch fails validation."""
        update_data = [
            {
                "$op": "add",
                "playlist_id": 9999,
                "name": 5
            }
        ]
        playlist_resource = PlaylistResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            playlist_resource.patch_collection(
                update_data)
        assert excinf.value.code == "validation_failure"

    @staticmethod
    def test_patch_collection_remove_fail(db_session):
        """Test removing from collection via patch fails validation."""
        update_data = [
            {
                "$op": "remove",
                "playlist_id": "test"
            }
        ]
        playlist_resource = PlaylistResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            playlist_resource.patch_collection(update_data)
        assert excinf.value.code == "validation_failure"

    @staticmethod
    def test_patch_collection_nested_opts(db_session):
        """Test nested opts work as expected."""
        data = [{
            "album_id": 1,
            "tracks": [{"track_id": 1}],
            "$options": {"tracks": {"partial": False}}
        }]
        resource = AlbumResource(session=db_session)
        resource.patch_collection(data)
        db_result = db_session.query(Album).filter(
            Album.album_id == 1).first()
        assert db_result is not None
        assert len(db_result.tracks) == 1

    # PUT TESTS

    @staticmethod
    def test_put_validation_fail(db_session):
        """Test put validation error failure."""
        resource = AlbumResource(session=db_session)
        with raises(UnprocessableEntityError) as excinf:
            resource.put(
                1,
                {"album_id": "bad"})
        assert excinf.value.code == "validation_failure"

    @staticmethod
    def test_put_resource_not_found(db_session):
        """Test put on a nonexistant resource fails."""
        resource = AlbumResource(session=db_session)
        with raises(ResourceNotFoundError) as excinf:
            resource.put(
                12345,
                {"title": "test"})
        assert excinf.value.code == "resource_not_found"

    # PUT COLLECTION TESTS

    @staticmethod
    def test_put_collection_fail(db_session):
        """Test that trying to put a collection fails."""
        update_data = []
        playlist_resource = PlaylistResource(session=db_session)
        with raises(MethodNotAllowedError) as excinf:
            playlist_resource.put_collection(update_data)
        assert excinf.value.code == "method_not_allowed"

    @staticmethod
    def test_put_permission_denied(db_session):
        """Test put permission denied errors work as expected."""
        resource = AlbumResource(session=db_session)
        data = {
            "album_id": 340,
            "title": "Denied"
        }
        with raises(PermissionDeniedError):
            resource.put((340,), data)

    # DELETE TESTS

    @staticmethod
    def test_delete(db_session):
        """Test a simple delete action."""
        resource = AlbumResource(session=db_session)
        resource.delete(1)
        result = db_session.query(Album).filter(
            Album.album_id == 1
        ).first()
        assert result is None

    @staticmethod
    def test_delete_resource_not_found(db_session):
        """Test deleting a non existent resource fails."""
        resource = AlbumResource(session=db_session)
        with raises(ResourceNotFoundError) as excinf:
            resource.delete(9999999)
        assert excinf.value.code == "resource_not_found"

    @staticmethod
    def test_delete_permission_denied(db_session):
        """Test delete permission denied errors work as expected."""
        resource = AlbumResource(session=db_session)
        with raises(PermissionDeniedError):
            resource.delete(340)

    # DELETE COLLECTION TESTS

    @staticmethod
    def test_delete_collection(db_session):
        """Test deleting from a collection works."""
        filters = {
            "playlist_id": 18
        }
        playlist_resource = PlaylistResource(session=db_session)
        result = playlist_resource.delete_collection(filters=filters)
        playlists = db_session.query(Playlist).filter(
            Playlist.playlist_id == 18).all()
        assert len(playlists) == 0
        assert result is None

    @staticmethod
    def test_delete_collection_permission_denied(db_session):
        """Test delete collection permission denied errors."""
        resource = AlbumResource(session=db_session)
        with raises(PermissionDeniedError):
            resource.delete_collection(filters={"album_id": 340})
