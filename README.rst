Drowsy
======

|Build Status| |Coverage Status| |Docs|

Query, update, and create SQLAlchemy objects via a RESTful API.

Shares some similarities with projects like Django-Tastypie and Flask-RESTful,
but is built around SQLAlchemy and Marshmallow to provide powerful nested
queries along with nested object updates and creation.




Current Status
--------------

Unstable. This library has undergone a pretty massive overhaul and become
heavily integrated with Marshmallow schemas. Don't use this as anything
other than a proof of concept or simply to toy around with for the immediate
future.



Key Features
------------
Given a series of SQLAlchemy models, corresponding schemas and resources based
off those models can be easily defined (or dynamically generated). By using those
resources, the following features are made available:

* Filter any resource collection by any field or sub resource field. Filters
  are not limited to an equality check, but can also handle ``>``, ``>=``,
  ``<=``, and ``<``, along with simple ``like`` text searches.
* Complex conditional filters may be applied to resources as well using
  MQLAlchemy's syntax.
* Easily override fields to prevent them from being queried, or define
  specific query whitelist rules.
* Sort and paginate resource collections.
* Resource representations can optionally include embedded resources.
* Create or update resources, including their own embedded resources, all
  in one API call and transaction.
* Parse filters, sorts, and pagination info from query params.
* Dynamically route all API requests to the appropriate resource.


TODO
----
* Improve test coverage.
* Improve documentation (especially the create/update/delete section).


Contributing
------------

Submit a pull request and make sure to include an updated AUTHORS
with your name along with an updated CHANGES.rst.


License
-------

MIT

.. |Build Status| image:: https://travis-ci.org/repole/drowsy.svg?branch=master
   :target: https://travis-ci.org/repole/drowsy
.. |Coverage Status| image:: https://coveralls.io/repos/repole/drowsy/badge.svg?branch=master
   :target: https://coveralls.io/r/repole/drowsy?branch=master
.. |Docs| image:: https://readthedocs.org/projects/drowsy/badge/?version=latest
   :target: http://drowsy.readthedocs.org/en/latest/
