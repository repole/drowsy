"""
    drowsy.tests.test_parser
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Parser tests for Drowsy.

    :copyright: (c) 2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from drowsy.schema import ResourceSchema
from drowsy.tests.base import DrowsyTests
from drowsy.tests.schemas import (
    AlbumCamelSchema
)
from drowsy.tests.models import Album


class DrowsySchemaTests(DrowsyTests):

    """Test drowsy query param parsing is working as expected."""

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
            class Meta:
                instance_cls = Album
                id_keys = ["album_id"]

            def get_instance(self, data):
                return None
        schema = TestSchema()
        result = schema.make_instance({"album_id": 1, "title": "test"})
        self.assertTrue(result.album_id == 1)
        self.assertTrue(result.title == "test")
        self.assertTrue(isinstance(result, Album))
