Drowsy
======

|Build Status| |Coverage Status| |Docs|

GraphQL type features in a REST API using SQLAlchemy and Marshmallow.

Drowsy aims to provide a similar feature set to GraphQL, and shares some
similarities with projects like Django-Tastypie and Flask-RESTful while
also being web framework agnostic.

Get started by visiting our Docs_ and checking out the Quickstart section.


Key Features
------------
Given a series of SQLAlchemy_ models, corresponding Marshmallow_ schemas and
Drowsy resources based off those models can be easily defined (or dynamically
generated). By using those resources, the following features are made available:

* Filter any resource collection by any field or nested resource field. Filters
  are not limited to an equality check, but can also handle ``>``, ``>=``,
  ``<=``, and ``<``, along with simple ``like`` text searches.
* Optionally embed nested resources within a result, enabling getting all child
  resources along with the parent resource in a single database query.
* Filter any embedded nested resource to get back only the child objects you
  want.
* Complex conditional filters may be applied to resources or nested resources
  as well using MQLAlchemy_ style syntax.
* Easily override fields to prevent them from being queried, or define specific
  query whitelist rules and permissions.
* Sort and paginate resource collections.
* Create or update resources, including their own nested resources, all in one
  API call and database transaction.
* Parse filters, sorts, and pagination info from query params.
* Dynamically route all API requests to the appropriate resource.


Requirements
------------

The project is largely built around Marshmallow_ and SQLAlchemy_. There has
been an explicit attempt to keep things modular and extensible, but if you
want to use a different ORM or different schema toolkit it'll take a good bit
of manual effort.

Drowsy is however web framework agnostic, and is capable of working with Flask,
CherryPy, Bottle.py, Falcon, or any other Python web framework.


Current Status
--------------

Beta. There's a good deal of testing and code coverage here, but the developer
API continues to evolve, so be prepared for things to break in future updates.


Contributing
------------

Submit a pull request to the dev branch and make sure to include an updated
AUTHORS with your name along with an updated CHANGES.rst.


License
-------

MIT

.. |Build Status| image:: https://travis-ci.org/repole/drowsy.svg?branch=master
   :target: https://travis-ci.org/repole/drowsy
.. |Coverage Status| image:: https://coveralls.io/repos/repole/drowsy/badge.svg?branch=master
   :target: https://coveralls.io/r/repole/drowsy?branch=master
.. |Docs| image:: https://readthedocs.org/projects/drowsy/badge/?version=latest
   :target: http://drowsy.readthedocs.org/en/latest/
.. _MQLAlchemy: http://mqlalchemy.readthedocs.org/
.. _SQLAlchemy: https://www.sqlalchemy.org/
.. _Marshmallow: https://marshmallow.readthedocs.io/
.. _Docs: https://readthedocs.org/projects/drowsy/badge/?version=latest
