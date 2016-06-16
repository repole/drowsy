.. _creating_updating:
.. module:: drowsy

Creating and Updating Resources
===============================

Currently the best documentation for creating and updating resources can be
found in the unit tests. In the future, this section will contain a much
more in depth breakdown of how to create and update resources.


Creating
--------

Simply send a POST request with all required fields filled out.
Note that child resources can be set by including a sub document
with their primary key.

Request:
.. sourcecode:: http

    POST /api/tracks HTTP1/1
    {
        "name": "Test Track Seven",
        "media_type": {
            "media_type_id": 2
        },
        "genre": {
            "name": "My New Genre"
        },
        "composer": "Nick Repole",
        "milliseconds": 206009,
        "bytes": 3305166,
        "unit_price": 0.99,
    }

Response:
.. sourcecode:: http

    HTTP/1.1 201 Created

    {
        "track_id": 400,
        "name": "Test Track Seven",
        "media_type": {
            "media_type_id": 2
            "name": "MPEG audio file",
            "self": "/media_types/1"
        },
        "genre": {
            "genre_id": 10
            "name": "My New Genre",
            "self": "/genres/20"
        },
        "composer": "Nick Repole",
        "milliseconds": 206009,
        "bytes": 3305166,
        "unit_price": 0.99,
        "self": "/tracks/400"
    }

Also note that posting multiple resources at once is as simple
as making the same request as above, but in list format.
