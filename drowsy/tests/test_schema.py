"""
    drowsy.tests.test_parser
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Parser tests for Drowsy.

    :copyright: (c) 2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from marshmallow import fields
from marshmallow.exceptions import ValidationError
from drowsy.convert import ModelResourceConverter
from drowsy.schema import ResourceSchema
from drowsy.tests.base import DrowsyTests
import drowsy.tests.resources
from drowsy.tests.schemas import (
    AlbumSchema, AlbumBadIdKeysSchema, AlbumCamelSchema, ArtistSchema,
    CustomerSchema, TrackPermissionsSchema, TrackSchema
)
from drowsy.tests.models import Album, Track


class DrowsySchemaTests(DrowsyTests):

    """Test drowsy schema classes are working as expected."""

    def test_schema_fields_by_load_from(self):
        """Test getting fields by their load_from value."""
        schema = AlbumCamelSchema(session=self.db_session)
        self.assertTrue("albumId" in schema.fields_by_load_from)

    def test_schema_default_get_instance(self):
        """Test a ResourceSchema handles get_instance properly."""
        class TestSchema(ResourceSchema):
            class Meta:
                instance_cls = Album
        self.assertTrue(isinstance(TestSchema().get_instance({}), Album))

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
                """Allows testing of the resource property.."""
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
        result, errors = schema.load(data=data)
        self.assertTrue(errors["albums"][0]["$op"][0])

    def test_schema_disallow_all_op_permissions(self):
        """Make sure permission denial works."""
        schema = TrackPermissionsSchema(session=self.db_session, partial=True)
        data = {
            "track_id": 1,
            "album": {"album_id": 1}
        }
        result, errors = schema.load(data=data)
        self.assertTrue(errors["album"])

    def test_schema_disallow_all_op_permissions_strict(self):
        """Make sure permission denial works."""
        schema = TrackPermissionsSchema(session=self.db_session, partial=True,
                                        strict=True)
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
        result, errors = schema.load(data=data)
        self.assertTrue(errors["tracks"][0]["bytes"])

    def test_schema_relationship_bad_data_strict(self):
        """Test bad data given to a relationship when strict fails."""
        schema = AlbumSchema(session=self.db_session, strict=True,
                             partial=True)
        data = {
            "artist": {"artist_id": "TEST"}
        }
        self.assertRaises(
            ValidationError,
            schema.load,
            data=data
        )

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
        result, errors = schema.load(data, partial=True)
        self.assertTrue(result.album.album_id == 347)

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
        result, errors = schema.load(data, partial=True, instance=instance)
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
        result, errors = schema.load(data, instance=instance)
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
            session=self.db_session, partial=True, strict=True)
        self.assertRaises(
            ValidationError,
            schema.load,
            data
        )

    def test_relationship_invalid_add(self):
        """Test trying to add a child to it's own parent fails."""
        data = {
            "album_id": 1,
            "tracks": [{
                "track_id": 1,
                "$op": "add"
            }]
        }
        schema = AlbumSchema(
            session=self.db_session, partial=True, strict=True)
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
            session=self.db_session, partial=True, strict=True)
        self.assertRaises(
            ValidationError,
            schema.load,
            data
        )
