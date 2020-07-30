.. _permissions:

Permissions Handling
====================

Given the wide scope of Drowsy, particularly with nested resources, the concept
of permissions and authorization can feel like a daunting one to dive into. The
good news is Drowsy was mindfully built to take permissions into account, and
it should be relatively straight forward to properly secure your API.

Because developers like to handle permissions in various ways, Drowsy attempts
to be as approach agnostic as possible, while still providing the basic tools
and entry points needed to implement permissions successfully.



Reading
-------

Fine grained control of what  different users can see happens at the Resource
level. Classes that inherit from :class:`~drowsy.resource.BaseModelResource`
include :meth:`~drowsy.resource.BaseModelResource.apply_required_filters`
which can usefully be overriden.

As an example, imagine you have a ``NotificationResource`` class, and would
like users to only be able to see their own notifications. To accomplish this,
your notification class might look something like:

.. code:: python

    class NotificationResource(ModelResource):
        class Meta:
            schema_cls = NotificationModelSchema

        def apply_required_filters(self, query, alias=None):
            """Ensure users can only see their own notifications."""
            # Use the provided model alias if applicable.
            # Note that this is what helps enforce required filters
            # on nested resources.
            model = alias or self.model
            # How user info is stored in the context dict is up to you.
            if self.context.get("user"):
                return query.filter(model.user_id == user.user_id)
            else:
                # hacky way to ensure the query always returns nothing
                return query.filter(model.user_id == -1)

Now when ``NotificationResource`` is accessed you can be assured that the above
filters will always be applied. Note that this also applies to nested
resources, so if you were to have a ``UserResource`` with a nested
``NotificationResource`` embedded, the above filters are still applied to the
nested collection of notifications.

An alternative, more conservative option exists, in overriding
:meth:`~drowsy.resource.BaseModelResource._check_method_allowed` on a Resource.
This method is called at the beginning of each request and has access to any
context the Resource was initialized with (e.g. which user is logged in), and
thus can be used to explicitly deny access to a certain method type (e.g.
denying a user access to GET or DELETE actions).

In such cases there's no fine grained control involved, the user is denied
a particular type of access to all objects in the collection.


Create, Update, and Delete
--------------------------

Like read permissions, mutation permissions have the option of overriding
:meth:`~drowsy.resource.BaseModelResource._check_method_allowed` to completely
restrict access.

More fine grained mutation control is handled at the schema level rather than
at the resource level. This allows validation to occur on an instance by
instance basis as data is being prepared for deserialization. In order to
implement permissions, you can override the
:meth:`~drowsy.schema.ResourceSchema.check_permission` method:


.. code:: python

    class NotificationSchema(ModelResourceSchema):
        class Meta:
            model = Notification

        def check_permission(self, data, instance, action):
            """Test if the proposed action is permissible.

            Note that other schema validation will run after this check,
            this is simply a high level check.

            :param dict data: The data to be loaded into an instance.
            :param instance: The existing instance this data is to be
                loaded into. ``None`` if creating a new instance.
            :param str action: Either ``"create"``, ``"update"``, or
                ``"delete"``.
            :return: None
            :raise PermissionDenied: If the action being taken is not
                allowed.

            """
            # How user info is stored in the context dict is up to you.
            user = self.context.get("user")
            if action == "delete":
                if not user.is_admin:
                    # Only allow admins to delete a notification.
                    raise PermissionDenied("Permission denied.")

In the above simple example, only admin users will be allowed to delete a
notification.


Relationship Operations
-----------------------

On occasion you'll find that you want to limit how different users can affect
different relationships. As an example, you might want to give a user the
ability to modify some metadata about an album, and some metadata about the
tracks on that album, but not be able to change which tracks belong to it.
In such a case, you'll need to set a ``permissions_cls`` on the relationship
you're trying to limit.


.. code:: python

    from drowsy.permissions import DisallowAllOpPermissions
    from drowsy.schema import ModelResourceSchema

    class AlbumSchema(ModelResourceSchema):
        class Meta:
            model = Track
            include_relationships = True
        tracks = Relationship(
            "TrackResource",
            many=True,
            permissions_cls=DisallowAllOpPermissions)

    class TrackSchema(ModelResourceSchema):
        class Meta:
            model = Track
            include_relationships = True
        album = Relationship(
            "AlbumResource",
            many=False,
            permissions_cls=DisallowAllOpPermissions)

Here we use the provided :class:`~drowsy.permissions.DisallowAllOpPermissions`
class to disallow any attempted changes to the ``tracks`` and ``album``
relationships. In most real world use cases, you'll want to roll your own
implementation of :class:`~drowsy.permissions.OpPermissionsABC` in order to
use the request context (e.g. which user is logged in) to determine what
relationship actions are allowed.

Note that in situations like this where there is a bidirectional relationship,
you must define permissions on both sides. This may seem inconvenient, but
there are scenarios where you'll want users to have different permissions
depending on which side of the relationship they're attempting to make changes
from. Perhaps you'd want all users who have access to modify albums the ability
to add tracks, but not all users who have access to modify tracks the ability
to change which album they belong to.
