.. _creating_updating:

Creating and Updating Resources
===============================

Creating and updating resources in Drowsy works just like any other typical
REST framework. POST is used to create object(s), PATCH to update, PUT to
completely replace, and of course DELETE works as you'd expect.

The thing that makes Drowsy different from most REST frameworks is that these
operations aren't limited to one type of resource at a time. For an example of
this, you can skip ahead to the (NESTED OPERATIONS) section to see an Album
getting created with a series of Tracks at the same time.

The below sections cover these operations in more detail, walking through the
simplest use cases to the most complex, using the example API referenced in
:ref:`quickstart` to demonstrate each situation.


Creating
--------

Simply send a POST request with all required fields filled out. Note that
the album table has a field ``artist_id``, which by default is hidden as
part of (de)serialization. Instead, to specify which Artist the Album belongs
to, include the nested relationship as part of the post data with the
identifier fields included to reference an existing Artist.

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


.. _nested_operations:

Nested Operations
-----------------

Creation and update operations don't have to be limited to the top level
resource(s) being written to, and can include modifications to nested objects
as well. In the below example, a new Album is created with two brand new
Tracks included as part of it, and one existing track added to it as well.

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

        "ablum_id": 349,
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

The benefit of the PATCH version on Album is that you can modify multiple
objects within a relationship at once in multiple different ways (e.g.
adding and removing at the some time).




* Write to nested collection
* Remove from nested collection
* Delete an individual resource
* Delete a collection of resources
* Create a resource
* Modify a resource
