"""
    drowsy.tests.test_parser
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Parser tests for Drowsy.

    :copyright: (c) 2016-2019 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from marshmallow import fields
from marshmallow.exceptions import ValidationError
from drowsy.convert import ModelResourceConverter
from drowsy.exc import PermissionDenied
from drowsy.schema import NestedOpts, ResourceSchema
from drowsy.tests.base import DrowsyTests
from drowsy.tests.schemas import (
    AlbumSchema, AlbumCamelSchema, ArtistSchema,
    CustomerSchema, TrackPermissionsSchema, TrackSchema
)
import drowsy.tests.resources
from drowsy.tests.models import Album, Track


class DrowsySchemaTests(DrowsyTests):

    """Test drowsy schema classes are working as expected."""

    def test_schema_default_get_instance(self):
        """Test a ResourceSchema handles get_instance properly."""
        class TestSchema(ResourceSchema):
            class Meta:
                instance_cls = Album
        self.assertIsNone(TestSchema().get_instance({}))

    def test_schema_default_id_keys(self):
        """Test a ResourceSchema handles given id_keys properly."""
        class TestSchema(ResourceSchema):
            class Meta:
                instance_cls = Album
                id_keys = ["album_id"]
        self.assertTrue("album_id" in TestSchema().id_keys)

    def test_schema_empty_id_keys(self):
        """Test a ResourceSchema handles no id_keys properly."""
        class TestSchema(ResourceSchema):
            class Meta:
                instance_cls = Album
        self.assertTrue(isinstance(TestSchema().id_keys, list))

    def test_schema_embed_top_level(self):
        """Test embedding a non nested field is treated like only."""
        schema = AlbumCamelSchema(session=self.db_session)
        schema.embed("album_id")
        self.assertTrue("album_id" in schema.only)

    def test_schema_embed_fail(self):
        """Test trying to embed a non-existent field fails."""
        schema = AlbumCamelSchema(session=self.db_session)
        self.assertRaises(
            AttributeError,
            schema.embed,
            "test"
        )

    def test_schema_make_instance_default(self):
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
        self.assertTrue(result.album_id == 1)
        self.assertTrue(result.title == "test")
        self.assertTrue(isinstance(result, Album))

    def test_schema_disallow_all_op_permissions_many(self):
        """Make sure permission denial on a list resource works."""
        schema = ArtistSchema(session=self.db_session)
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
        self.assertTrue(errors["albums"][0]["$op"][0])

    def test_schema_disallow_all_op_permissions(self):
        """Make sure permission denial works."""
        schema = TrackPermissionsSchema(session=self.db_session, partial=True)
        data = {
            "track_id": 1,
            "album": {"album_id": 1}
        }
        errors = {}
        try:
            schema.load(data=data)
        except ValidationError as exc:
            errors = exc.messages
        self.assertTrue(errors["album"])

    def test_schema_disallow_all_op_permissions_strict(self):
        """Make sure permission denial works."""
        schema = TrackPermissionsSchema(session=self.db_session, partial=True)
        data = {
            "track_id": 1,
            "album": {"album_id": 1}
        }
        self.assertRaises(
            ValidationError,
            schema.load,
            data=data
        )

    def test_schema_relationship_bad_data(self):
        """Test bad data supplied to a relationship fails properly."""
        schema = AlbumSchema(session=self.db_session, partial=True)
        data = {
            "tracks": [{"bytes": "TEST"}]
        }
        errors = {}
        try:
            schema.load(data=data)
        except ValidationError as exc:
            errors = exc.messages
        self.assertTrue(errors["tracks"][0]["bytes"])

    def test_convert_property2field_instance(self):
        """Test property2field can return a column type."""
        converter = ModelResourceConverter()
        result = converter.property2field(Album.album_id.prop, instance=False)
        self.assertTrue(
            result == fields.Integer
        )

    def test_convert_doc_string(self):
        """Test converter properly handles a doc string."""
        schema = CustomerSchema(session=self.db_session)
        self.assertTrue(schema.fields["state"].metadata["description"] ==
                        "Two Character Abbreviation")

    def test_relationship_set_child(self):
        """Test setting a non list relationship works."""
        data = {
            "track_id": 1,
            "album": {
                "album_id": 347,
            }
        }
        schema = TrackSchema(session=self.db_session)
        result = schema.load(data, partial=True)
        self.assertTrue(result.album.album_id == 347)

    def test_many_load(self):
        """Test loading many objects at once works."""
        data = [
            {"track_id": 1, "name": "test1"},
            {"track_id": 2, "name": "test2"},
            {"track_id": 3, "name": "test3"},
            {"track_id": 4, "name": "test4"},
            {"track_id": 5, "name": "test5"}
        ]
        schema = TrackSchema(session=self.db_session, many=True)
        result = schema.load(data, partial=True, many=True)
        self.assertTrue(len(result) == 5)

    def test_many_load_failure(self):
        """Test loading many objects with bad data fails accordingly."""
        data = [
            {"track_id": 1, "name": 1},
            {"track_id": 2, "name": 2},
            {"track_id": 3, "name": "test3"},
            {"track_id": 4, "name": "test4"},
            {"track_id": 5, "name": "test5"}
        ]
        schema = TrackSchema(session=self.db_session, many=True)
        errors = {}
        try:
            schema.load(data, partial=True, many=True)
        except ValidationError as exc:
            errors = exc.messages
        self.assertTrue(len(errors.keys()) == 2)
        self.assertTrue(0 in errors and 1 in errors)

    def test_base_instance_relationship_set_child(self):
        """Test setting a child when loading with a base instance."""
        album = self.db_session.query(Album).filter(
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
        schema = TrackSchema(session=self.db_session)
        result = schema.load(data, partial=True, instance=instance)
        self.assertTrue(result.album.album_id == 1)

    def test_base_instance_relationship_add_child(self):
        """Test adding a child when loading with a base instance."""
        track = self.db_session.query(Track).filter(
            Track.track_id == 1).first()
        instance = Album(album_id=9999)
        instance.tracks.append(track)
        data = {
            "album_id": 1,
            "tracks": [
                {"track_id": 1}
            ]
        }
        schema = AlbumSchema(session=self.db_session, partial=True)
        result = schema.load(data, instance=instance)
        self.assertTrue(result.tracks[0].track_id == 1)

    def test_relationship_invalid_remove(self):
        """Test trying to remove a child from the wrong parent fails."""
        data = {
            "album_id": 1,
            "tracks": [{
                "track_id": 597,
                "$op": "remove"
            }]
        }
        schema = AlbumSchema(
            session=self.db_session, partial=True)
        self.assertRaises(
            ValidationError,
            schema.load,
            data
        )

    def test_relationship_invalid_op(self):
        """Test an invalid operation on a relationship fails."""
        data = {
            "album_id": 1,
            "tracks": [{
                "track_id": 1,
                "$op": "test"
            }]
        }
        schema = AlbumSchema(
            session=self.db_session, partial=True)
        self.assertRaises(
            ValidationError,
            schema.load,
            data
        )

    def test_instance_relationship_nested_opts(self):
        """Test nested opts enable complete relation replacement."""
        data = {
            "album_id": 2,
            "tracks": [
                {"track_id": 1}
            ]
        }
        nested_opts = {"tracks": NestedOpts(partial=False)}
        schema = AlbumSchema(session=self.db_session, nested_opts=nested_opts,
                             partial=True)
        result = schema.load(data)
        self.assertTrue(result.tracks[0].track_id == 1)
        self.assertTrue(len(result.tracks) == 1)

    def test_nested_relationship_nested_opts(self):
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
        schema = AlbumSchema(session=self.db_session, nested_opts=nested_opts,
                             partial=True)
        result = schema.load(data)
        self.assertTrue(len(result.tracks[0].playlists) == 1)

    def test_permission_denied(self):
        """Test permission denied errors work as expected."""
        data = {
            "album_id": 340,
            "title": "Denied"
        }
        schema = AlbumSchema(session=self.db_session, partial=True)
        self.assertRaises(PermissionDenied, schema.load, data)
