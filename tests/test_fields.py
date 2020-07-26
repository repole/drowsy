"""
    drowsy.tests.test_fields
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Fields tests for Drowsy.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from pytest import raises
from collections import namedtuple
from drowsy.base import EmbeddableMixinABC, NestedPermissibleABC
from drowsy.fields import APIUrl, Relationship
from drowsy.permissions import OpPermissionsABC
from .resources import AlbumResource, TrackResource
from .schemas import AlbumSchema


def test_permissions_abc_check():
    """Test that permissions abc fails."""
    with raises(NotImplementedError):
        OpPermissionsABC().check(
            operation="add",
            obj_data=None)


def test_field_embeddable_mixin_abc_deserialize():
    """Test that the embeddable mixin can't be deserialized."""
    with raises(NotImplementedError):
        EmbeddableMixinABC().deserialize("test")


def test_field_embeddable_mixin_abc_serialize():
    """Test that the embeddable mixin can't be serialized."""
    with raises(NotImplementedError):
        EmbeddableMixinABC().serialize("test", "test")


def test_field_nested_permissible_abc_parent_child():
    """Test nested permissibles fail to check parent for child."""
    with raises(NotImplementedError):
        NestedPermissibleABC(AlbumResource)._parent_contains_child(
            "test",
            "test")


def test_field_nested_permissible_abc_get_id_instance():
    """Test nested permissibles fail to get an id instance."""
    with raises(NotImplementedError):
        NestedPermissibleABC(AlbumResource)._get_identified_instance(
            obj_data={})


def test_field_nested_permissible_abc_perform_op():
    """Test nested permissibles fail to perform operation."""
    with raises(NotImplementedError):
        NestedPermissibleABC(AlbumResource)._perform_operation(
            operation="add",
            parent=None,
            instance=None,
            errors={},
            index=None
        )


def test_field_nested_permissible_load_existing():
    """Test nested permissibles fail to get an existing instance."""
    with raises(NotImplementedError):
        NestedPermissibleABC(AlbumResource)._load_existing_instance(
            obj_data=None,
            instance=None
        )


def test_field_nested_permissible_load_new():
    """Test nested permissibles fail to get a new instance."""
    with raises(NotImplementedError):
        NestedPermissibleABC(AlbumResource)._load_new_instance(
            obj_data=None)


def test_field_nested_resource_provided(db_session):
    """Test providing a resource to a Relationship works."""
    resource = AlbumResource(session=db_session)
    field = Relationship(nested=resource)
    assert field.resource == resource


def test_field_nested_resource_class_provided(db_session):
    """Test providing a resource class to a Relationship works."""

    class TestSchema(AlbumSchema):
        tracks = Relationship(nested=TrackResource)

    schema = TestSchema(session=db_session)
    assert isinstance(schema.fields["tracks"].resource,
                      TrackResource)


def test_field_bad_nested_resource_provided():
    """Test providing a resource to a Relationship works."""
    field = Relationship(nested=1)
    with raises(ValueError):
        getattr(field, "resource")


def test_field_api_url_serialize():
    """Test ApiUrl serializes properly."""
    field = APIUrl(endpoint_name="test", base_url="drowsy.com")
    Parent = namedtuple("Parent", ["id_keys"])
    TestObj = namedtuple("TestObj", ["test_id"])
    field.parent = Parent(id_keys=["test_id"])
    result = field.serialize("url", obj=TestObj(test_id=5))
    assert result == "drowsy.com/test/5"


def test_field_api_url_serialize_slash():
    """Test ApiUrl serialization with trailing slash base url."""
    field = APIUrl(endpoint_name="test", base_url="drowsy.com/")
    Parent = namedtuple("Parent", ["id_keys"])
    TestObj = namedtuple("TestObj", ["test_id"])
    field.parent = Parent(id_keys=["test_id"])
    result = field.serialize("url", obj=TestObj(test_id=5))
    assert result == "drowsy.com/test/5"
