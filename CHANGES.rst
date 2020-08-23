=======
Changes
=======

Release 0.1.1 (in progress)
===========================

Bug Fixes
---------
* Fix ``ModelResourceConverter`` to include a Foreign Key when it's also a
  Primary Key, even if ``include_fk`` is set to ``False``.
* Fix ``convert_key_name`` bug causing it to fail with
  ``CamelModelResourceConverter``.


Release 0.1.0
=============

Features added
--------------
* Permission handling for resource CRUD operations.
* Permission handling for relationship operations.
* Ability to properly handle nested required filters.
