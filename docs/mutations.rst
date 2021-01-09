.. _creating_updating:

Mutations
=========

Creating, updating, and deleting resources in Drowsy works just like any other
typical REST framework. POST is used to create object(s), PATCH to update, PUT
to completely replace, and of course DELETE works as you'd expect.

The thing that makes Drowsy different from most REST frameworks is that these
operations aren't limited to one type of resource at a time. For an example of
this, you can skip ahead to the :ref:`nested_operations` section to see an
Album getting created with a series of Tracks at the same time.

The below sections cover these operations in more detail, walking through the
simplest use cases to the most complex, using the example API referenced in
:ref:`quickstart` to demonstrate each situation.


Creating
--------

To create a new object, send a POST request with all required fields filled
out. Note that the album table has a field ``artist_id``, which by default is
hidden as part of (de)serialization. Instead, to specify which Artist the Album
belongs to, include the nested relationship as part of the post data with the
identifier field (in most cases the primary key) included to reference an
existing Artist.

Request:

.. sourcecode:: http

    POST /api/albums HTTP/1.1

    {
        "title": "A New AC/DC Album",
        "artist": {
            "artist_id": 1
        }
    }

Response:

.. sourcecode:: http

    HTTP/1.1 201 Created

    {
        "album_id": 348,
        "title": "A New AC/DC Album",
        "artist": {
            "artist_id": 1,
            "name": "AC/DC",
            "self": "/api/artists/1"
        }
    }

More info on how creating/modifying relationships can be found in the
:ref:`nested_operations` section.


Collection Creating
-------------------

Posting multiple resources at once is as simple as making the same request
as above, but in list format.

Creating multiple objects at once works nearly identically to creating a
single object, with the only distinction being the use of a list of objects
rather than a single object in the POST body:

.. sourcecode:: http

    POST /api/albums HTTP/1.1

    [
        {
            "title": "A New AC/DC Album",
            "artist": {
                "artist_id": 1
            }
        },
        {
            "title": "A New Aerosmith Album",
            "artist": {
                "artist_id": 3
            }
        }
    ]


Updating
--------

Updating an object works similarly to creating an object, with the only
difference being the HTTP method used (PATCH) and that the pre-existing
object is specified directly in the URL using it's
:attr:`~drowsy.schema.ModelResourceSchema.id_keys` value(s).

Request:

.. sourcecode:: http

    PATCH /api/albums/1 HTTP/1.1

    {
        "title": "For Those About To Rock We Salute You (live)"
    }

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK

    {
        "album_id": 1,
        "artist": {
            "artist_id": 1,
            "name": "AC/DC",
            "self": "/api/artists/1"
        },
        "title": "For Those About To Rock We Salute You (live)"
    }

You can also make a PUT request if you desire to replace the entire object.
The only difference from PATCH is that you must provide values for all fields
that would be required when creating a new object.

There's also the option of atomically updating a single field specifically,
if you so desire:

Request:

.. sourcecode:: http

    PATCH /api/albums/1/title HTTP/1.1

    "For Those About To Rock We Salute You (live)"

Response:

.. sourcecode:: http

    HTTP/1.1 200 OK

    "For Those About To Rock We Salute You (live)"

In such cases the use of POST, PATCH, and PATCH all act equivalently.


Collection Updating
-------------------

Performing multiple modifications to a collection involves submitting a PATCH
or PUT request to the collection itself. PATCH in this case means making in
place modifications to the collection, while PUT means essentially emptying the
collection and starting over.

An example of PATCH first:

.. sourcecode:: http

    PATCH /api/albums HTTP/1.1

    [
        {
            "album_id": 1,
            "title": "For Those About To Rock We Salute You (live)"
        },
        {
            "album_id": 2,
            "$op": "remove"
        },
        {
            "title": "A New AC/DC Album",
            "artist": {
                "artist_id": 1
            }
        }
    ]

Response:

.. sourcecode:: http

    HTTP/1.1 204 No Content

The result of the above request is the Album with ``album_id=1`` gets it's
title updated, the Album with ``album_id=2`` gets removed from the collection
(deleting it), and ``"A New AC/DC Album"`` is created and added to the
collection. All other objects in the collection remain unmodified. For more
information on how the ``"$op"`` field works, see :ref:`nested_operations`.

PUT acts differently from PATCH in that it replaces the contents of the
entire collection:

.. sourcecode:: http

    PUT /api/albums HTTP/1.1

    [
        {
            "album_id": 1,
            "title": "For Those About To Rock We Salute You (live)"
        },
        {
            "title": "A New AC/DC Album",
            "artist": {
                "artist_id": 1
            }
        }
    ]

Response:

.. sourcecode:: http

    HTTP/1.1 204 No Content

In this case, albums will now only contain two records, the ones explicitly
included in the request. Note that we didn't need to explicitly remove
``album_id=2`` like we did in the PATCH version of this request, since that
happens by default.


Deleting
--------

Removing objects is generally a simple process on the surface, where making a
DELETE request to a specific object will attempt to delete it:

.. sourcecode:: http

    DELETE /api/albums/1 HTTP/1.1

Response:

.. sourcecode:: http

    HTTP/1.1 204 No Content

In practice, DELETE can fail for a number of reasons related to relationships,
and is the most likely part of Drowsy not to work the way you expect out of the
box. Generally speaking, Drowsy is at the mercy of how you've set up your
foreign key and relationship cascades.

It's up to you to decide how you'd want such an attempt to delete an Album to
impact it's children Tracks. In the
`models used in our example API <_modules/examples/chinook_api/models.html>`_,
note that on the ``Track.album`` relationship, a backref is used to create
the ``Album.tracks`` relationship, and the cascade rule of ``"delete-orphan"``
is used in this case to specify that the deletion of an Album should cascade
to all of its Tracks.


Collection Deleting
-------------------

Deleting an entire collection of objects is as simple as a DELETE request to
the collection endpoint:

.. sourcecode:: http

    DELETE /api/albums HTTP/1.1

Response:

.. sourcecode:: http

    HTTP/1.1 204 No Content


You also have the option of specifying filters and complex queries in the same
fashion that you would on a GET request (see :ref:`querying`) to help narrow
down which objects you actually want to delete.


.. _nested_operations:

Nested Operations
-----------------

Creation and update operations don't have to be limited to the top level
resource(s) being written to, and can include modifications to nested objects
as well. In the below example, a new Album is created with two brand new
Tracks included as part of it, and one existing Track added to it as well.

.. sourcecode:: http

    POST /api/album HTTP/1.1

    {

        "title": "Flash Gordon",
        "artist": {
            "artist_id": 51
        },
        "tracks": [
            {
                "name": "Flash's Theme",
                "composer": "Brian May",
                "milliseconds": "211009",
                "bytes": "3305166",
                "unit_price": "0.99"
            },
            {
                "name": "In the Space Capsule (The Love Theme)",
                "composer": "Roger Taylor",
                "milliseconds": "163020",
                "bytes": "3134286",
                "unit_price": "0.99"
            },
            {
                "$op": "add",
                "track_id": 1
            }
        ]
    }

Note that the ``"$op": "add"`` portion of this is optional, but is an
explicit way of telling drowsy to add this Track. By default, if an object
is referenced in a relationship like this, the implicit action is always
to add it.

Say we realize that adding a Track was a mistake, we can explicitly remove
it like so:

.. sourcecode:: http

    PATCH /api/album HTTP/1.1

    {

        "album_id": 349,
        "tracks": [
            {
                "$op": "remove",
                "track_id": 1
            }
        ]
    }

This is analogous to a DELETE request to the subresource itself:

.. sourcecode:: http

    DELETE /api/album/349/tracks/1 HTTP/1.1

Or similarly you could remove all Tracks from the Album:

.. sourcecode:: http

    DELETE /api/album/349/tracks HTTP/1.1

The benefit of the PATCH version on Album rather than this more explicit DELETE
statement is that you can modify multiple objects within a relationship at once
in multiple different ways (e.g. adding and removing at the some time).

It's also important to note that the same way you can send a DELETE request to
a subresource, POST, PATCH, and PUT work how you'd expect them to. Sending a
POST or PATCH request containing a list of Tracks to ``/api/albums/1/tracks``
will add those Tracks to the Album. A PUT request to the same URL will replace
the contents of that relationship with the list of Tracks you send.


Limitations
-----------

Nested operations inherently mean there are opportunities to make circular
references and refer to the same relationship or object multiple times in the
same request. Drowsy doesn't have a way to explicitly detect that a particular
object was already updated as part of a request, and thus these types of
requests may have unintended consequences.

Consider two Playlists that both contain the same Track. A PATCH request to
``/api/playlists`` in which the same child Track has part of it's information
modified in the ``tracks`` collection of both Playlists does not have any
guaranteed behavior. As of now, the Track will end up with the values that
were processed last by SQLAlchemy, but in future updates we may explicitly
detect and prevent such operations, so don't rely on that behavior to
always work.


More Examples
-------------

If you're looking for more examples, try taking a look through the included
test suite, in particular the
`test_resource.py <_modules/tests/test_resource.html#TestDrowsyResource>`_ file.
