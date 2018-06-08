"""
    drowsy.tests.test_fields
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Fields tests for Drowsy.

    :copyright: (c) 2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from drowsy.base import EmbeddableMixinABC, NestedPermissibleABC
from drowsy.fields import Relationship
from drowsy.permissions import OpPermissionsABC
from drowsy.tests.resources import AlbumResource, TrackResource
from drowsy.tests.schemas import AlbumSchema
from drowsy.tests.base import DrowsyTests


class DrowsyFieldTests(DrowsyTests):

    """Test drowsy fields are working as expected."""

    def test_permissions_abc_check(self):
        """Test that permissions abc fails."""
        self.assertRaises(
            NotImplementedError,
            OpPermissionsABC().check,
            operation=None,
            obj_data=None
        )

    def test_field_embeddable_mixin_abc_deserialize(self):
        """Test that the embeddable mixin can't be deserialized."""
        self.assertRaises(
            NotImplementedError,
            EmbeddableMixinABC().deserialize,
            "test"
        )

    def test_field_embeddable_mixin_abc_serialize(self):
        """Test that the embeddable mixin can't be serialized."""
        self.assertRaises(
            NotImplementedError,
            EmbeddableMixinABC().serialize,
            "test",
            "test"
        )

    def test_field_nested_permissible_abc_parent_child(self):
        """Test nested permissibles fail to check parent for child."""
        self.assertRaises(
            NotImplementedError,
            NestedPermissibleABC(AlbumResource)._parent_contains_child,
            "test",
            "test"
        )

    def test_field_nested_permissible_abc_get_id_instance(self):
        """Test nested permissibles fail to get an id instance."""
        self.assertRaises(
            NotImplementedError,
            NestedPermissibleABC(AlbumResource)._get_identified_instance,
            obj_data={}
        )

    def test_field_nested_permissible_abc_perform_op(self):
        """Test nested permissibles fail to perform operation."""
        self.assertRaises(
            NotImplementedError,
            NestedPermissibleABC(AlbumResource)._perform_operation,
            operation=None,
            parent=None,
            instance=None,
            errors=None,
            index=None
        )

    def test_field_nested_permissible_load_existing(self):
        """Test nested permissibles fail to get an existing instance."""
        self.assertRaises(
            NotImplementedError,
            NestedPermissibleABC(AlbumResource)._load_existing_instance,
            obj_data=None,
            instance=None
        )

    def test_field_nested_permissible_load_new(self):
        """Test nested permissibles fail to get a new instance."""
        self.assertRaises(
            NotImplementedError,
            NestedPermissibleABC(AlbumResource)._load_new_instance,
            obj_data=None
        )

    def test_field_nested_resource_provided(self):
        """Test providing a resource to a Relationship works."""
        resource = AlbumResource(session=self.db_session)
        field = Relationship(nested=resource)
        self.assertTrue(field.resource == resource)

    def test_field_nested_resource_class_provided(self):
        """Test providing a resource class to a Relationship works."""
        class TestSchema(AlbumSchema):
            tracks = Relationship(nested=TrackResource)
        schema = TestSchema(session=self.db_session)
        self.assertTrue(
            isinstance(schema.fields["tracks"].resource, TrackResource))

    def test_field_bad_nested_resource_provided(self):
        """Test providing a resource to a Relationship works."""
        field = Relationship(nested=1)
        self.assertRaises(
            ValueError,
            getattr,
            field,
            "resource"
        )




