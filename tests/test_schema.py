"""
    drowsy.tests.test_parser
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Parser tests for Drowsy.

    :copyright: (c) 2016-2019 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow import fields
from marshmallow.exceptions import ValidationError
from drowsy.convert import ModelResourceConverter
from drowsy.exc import PermissionValidationError
from drowsy.schema import NestedOpts, ResourceSchema
from tests.base import DrowsyDatabaseTests
from tests.schemas import (
    AlbumSchema, AlbumCamelSchema, ArtistSchema,
    CustomerSchema, TrackPermissionsSchema, TrackSchema
)
import tests.resources
from tests.models import Album, Track
from pytest import raises


def test_schema_default_get_instance():
    """Test a ResourceSchema handles get_instance properly."""
    class TestSchema(ResourceSchema):
        class Meta:
            instance_cls = Album
    assert TestSchema().get_instance({}) is None


def test_schema_fail_missing_key():
    """Test schema failure missing key error message."""
    schema = AlbumSchema()
    with raises(AssertionError):
        schema.make_error(key="test")


def test_schema_default_id_keys():
    """Test a ResourceSchema handles given id_keys properly."""
    class TestSchema(ResourceSchema):
        class Meta:
            instance_cls = Album
            id_keys = ["album_id"]
    assert "album_id" in TestSchema().id_keys


def test_schema_empty_id_keys():
    """Test a ResourceSchema handles no id_keys properly."""
    class TestSchema(ResourceSchema):
        class Meta:
            instance_cls = Album
    assert isinstance(TestSchema().id_keys, list)


def test_schema_make_instance_default():
    """Test making an instance from a non model schema."""
    class TestSchema(ResourceSchema):
        """Simple schema for this test."""
        class Meta:
            """Meta options for this schema."""
            instance_cls = Album
            id_keys = ["album_id"]

        def get_instance(self, data):
            """Allows testing of the resource property."""
            return None
    schema = TestSchema()
    result = schema.make_instance({"album_id": 1, "title": "test"})
    assert result.album_id == 1
    assert result.title == "test"
    assert isinstance(result, Album)


def test_convert_property2field_instance():
    """Test property2field can return a column type."""
    converter = ModelResourceConverter()
    result = converter.property2field(Album.album_id.prop, instance=False)
    assert result == fields.Integer


class TestDrowsySchema(DrowsyDatabaseTests):

    """Test drowsy schema classes are working as expected."""

    @staticmethod
    def test_schema_embed_top_level(db_session):
        """Test embedding a non nested field is treated like only."""
        schema = AlbumCamelSchema(session=db_session)
        schema.embed("album_id")
        assert "album_id" in schema.only

    @staticmethod
    def test_schema_embed_fail(db_session):
        """Test trying to embed a non-existent field fails."""
        schema = AlbumCamelSchema(session=db_session)
        with raises(AttributeError):
            schema.embed("test")

    @staticmethod
    def test_schema_disallow_all_op_permissions_many(db_session):
        """Make sure permission denial on a list resource works."""
        schema = ArtistSchema(session=db_session)
        data = {
            "artist_id": 1,
            "name": "test",
            "albums": [
                {"album_id": 1}
            ]
        }
        errors = {}
        try:
            schema.load(data=data)
        except ValidationError as exc:
            errors = exc.messages
        assert errors["albums"][0]["$op"][0]

    @staticmethod
    def test_schema_disallow_all_op_permissions(db_session):
        """Make sure permission denial works."""
        schema = TrackPermissionsSchema(session=db_session, partial=True)
        data = {
            "track_id": 1,
            "album": {"album_id": 1}
        }
        errors = {}
        try:
            schema.load(data=data)
        except ValidationError as exc:
            errors = exc.messages
        assert errors["album"]

    @staticmethod
    def test_schema_disallow_all_op_permissions_strict(db_session):
        """Make sure permission denial works."""
        schema = TrackPermissionsSchema(session=db_session, partial=True)
        data = {
            "track_id": 1,
            "album": {"album_id": 1}
        }
        with raises(ValidationError):
            schema.load(data=data)

    @staticmethod
    def test_schema_relationship_bad_data(db_session):
        """Test bad data supplied to a relationship fails properly."""
        schema = AlbumSchema(session=db_session, partial=True)
        data = {
            "tracks": [{"bytes": "TEST"}]
        }
        errors = {}
        try:
            schema.load(data=data)
        except ValidationError as exc:
            errors = exc.messages
        assert errors["tracks"][0]["bytes"]

    @staticmethod
    def test_convert_doc_string(db_session):
        """Test converter properly handles a doc string."""
        schema = CustomerSchema(session=db_session)
        assert (schema.fields["state"].metadata["description"] ==
                "Two Character Abbreviation")

    @staticmethod
    def test_relationship_set_child(db_session):
        """Test setting a non list relationship works."""
        data = {
            "track_id": 1,
            "album": {
                "album_id": 347,
            }
        }
        schema = TrackSchema(session=db_session)
        result = schema.load(data, partial=True)
        assert result.album.album_id == 347

    @staticmethod
    def test_many_load(db_session):
        """Test loading many objects at once works."""
        data = [
            {"track_id": 1, "name": "test1"},
            {"track_id": 2, "name": "test2"},
            {"track_id": 3, "name": "test3"},
            {"track_id": 4, "name": "test4"},
            {"track_id": 5, "name": "test5"}
        ]
        schema = TrackSchema(session=db_session, many=True)
        result = schema.load(data, partial=True, many=True)
        assert len(result) == 5

    @staticmethod
    def test_many_load_failure(db_session):
        """Test loading many objects with bad data fails accordingly."""
        data = [
            {"track_id": 1, "name": 1},
            {"track_id": 2, "name": 2},
            {"track_id": 3, "name": "test3"},
            {"track_id": 4, "name": "test4"},
            {"track_id": 5, "name": "test5"}
        ]
        schema = TrackSchema(session=db_session, many=True)
        errors = {}
        try:
            schema.load(data, partial=True, many=True)
        except ValidationError as exc:
            errors = exc.messages
        assert len(errors.keys()) == 2
        assert 0 in errors and 1 in errors

    @staticmethod
    def test_base_instance_relationship_set_child(db_session):
        """Test setting a child when loading with a base instance."""
        album = db_session.query(Album).filter(
            Album.album_id == 1).first()
        instance = Track(track_id=9999, album=album)
        data = {
            "track_id": 9999,
            "album": {
                "album_id": 1,
            },
            "name": "New TestTrack",
            "media_type": {
                "media_type_id": 1
            },
            "milliseconds": 1,
            "unit_price": 1.0
        }
        schema = TrackSchema(session=db_session)
        result = schema.load(data, partial=True, instance=instance)
        assert result.album.album_id == 1

    @staticmethod
    def test_base_instance_relationship_add_child(db_session):
        """Test adding a child when loading with a base instance."""
        track = db_session.query(Track).filter(
            Track.track_id == 1).first()
        instance = Album(album_id=9999)
        instance.tracks.append(track)
        data = {
            "album_id": 1,
            "tracks": [
                {"track_id": 1}
            ]
        }
        schema = AlbumSchema(session=db_session, partial=True)
        result = schema.load(data, instance=instance)
        assert result.tracks[0].track_id == 1

    @staticmethod
    def test_relationship_invalid_remove(db_session):
        """Test trying to remove a child from the wrong parent fails."""
        data = {
            "album_id": 1,
            "tracks": [{
                "track_id": 597,
                "$op": "remove"
            }]
        }
        schema = AlbumSchema(
            session=db_session, partial=True)
        with raises(ValidationError):
            schema.load(data)

    @staticmethod
    def test_relationship_invalid_op(db_session):
        """Test an invalid operation on a relationship fails."""
        data = {
            "album_id": 1,
            "tracks": [{
                "track_id": 1,
                "$op": "test"
            }]
        }
        schema = AlbumSchema(
            session=db_session, partial=True)
        with raises(ValidationError):
            schema.load(data)

    @staticmethod
    def test_instance_relationship_nested_opts(db_session):
        """Test nested opts enable complete relation replacement."""
        data = {
            "album_id": 2,
            "tracks": [
                {"track_id": 1}
            ]
        }
        nested_opts = {"tracks": NestedOpts(partial=False)}
        schema = AlbumSchema(session=db_session, nested_opts=nested_opts,
                             partial=True)
        result = schema.load(data)
        assert result.tracks[0].track_id == 1
        assert len(result.tracks) == 1

    @staticmethod
    def test_nested_relationship_nested_opts(db_session):
        """Test nested opts enable complete relation replacement."""
        data = {
            "album_id": 2,
            "tracks": [
                {"track_id": 1,
                 "playlists": [
                     {"playlist_id": 1}
                 ]}
            ]
        }
        nested_opts = {
            "tracks": NestedOpts(partial=False),
            "tracks.playlists": NestedOpts(partial=False)}
        schema = AlbumSchema(session=db_session, nested_opts=nested_opts,
                             partial=True)
        result = schema.load(data)
        assert len(result.tracks[0].playlists) == 1

    @staticmethod
    def test_permission_denied(db_session):
        """Test permission denied errors work as expected."""
        data = {
            "album_id": 340,
            "title": "Denied"
        }
        schema = AlbumSchema(session=db_session, partial=True)
        with raises(PermissionValidationError):
            schema.load(data)

    @staticmethod
    def test_permission_denied_list(db_session):
        """Test permission denied errors for lists work as expected."""
        data = [{"track_id": 1, "name": "Denied"}]
        schema = TrackSchema(session=db_session, partial=True)
        with raises(PermissionValidationError):
            schema.load(data, many=True)
