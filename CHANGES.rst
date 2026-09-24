.. _changelog:

Changelog
*********

This document describes the changes in the DEAPI library.

Changes are filed as fragment files in ``upcoming_changes/`` and assembled into this
file by `towncrier <https://towncrier.readthedocs.io/>`_ when a release is prepared
(see ``upcoming_changes/README.rst``).

.. towncrier release notes start

5.3.0 (2026-09-24)
==================

New Features
------------

- ``pydeserver --twin`` serves frames rendered by the `de-twin <https://github.com/directelectron/de-twin>`_ digital twin instead of the built-in fake data: a simulated microscope, specimen and detector, with a DE-TEM-Channel (``--soap-port``) so stage and optics changes show up in the images. Install it with ``pip install "deapi[twin]"``. (`#59 <https://github.com/directelectron/deapi/pull/59>`_)


Bug Fixes
---------

- Fixed virtual masks and XY scan arrays sometimes arriving incomplete, which hung the connection (seen on macOS): the client now sends every byte of them. (`#60 <https://github.com/directelectron/deapi/pull/60>`_)


Documentation
-------------

- Added an example that moves the stage with ``de_microscope`` and images holes in a grid, run against the digital twin. (`#59 <https://github.com/directelectron/deapi/pull/59>`_)


Maintenance
-----------

- The simulated server closes a connection after an error, so the client gets an error instead of waiting; the test suite only stops deapi's own simulated server on port 13240, never a real DE-Server. (`#60 <https://github.com/directelectron/deapi/pull/60>`_)
- Releases are prepared by the **Prepare Release** workflow, and the changelog is assembled from towncrier fragments in ``upcoming_changes/``, as in the other Direct Electron Python packages. (`#61 <https://github.com/directelectron/deapi/pull/61>`_)


5.3.beta6
=========
- Fixed invalid property errors and bugs in set_binning
- Updated get_property_specifications
- Do not automatically set attributes.windowWidth and attributes.windowHeight
- Return pattern index for get_result and get_virtual_image_buffer

5.3.beta5
=========
- Modify gain acquisition

5.3.beta4
=========
- Add GetEvent functionality to client.py
- Fixed bug in set_binning

5.3.beta3
=========
- Fix the problem that the set_binning function could not set HW binning to 1

5.3.beta2
=========
- Add access register

5.3.beta1
=========
- Create a Result Class to handle Result + Histogram

5.3.beta0
=========
- Add support for binning in x/ y dimensions when returning a result (#19)

5.2.2
==========
- Initial release
- Renamed `Client` functions from CamelCase to snake_case (Legacy functions are still available)
- Added buffer_protocol module for handling different buffer protocol files
- Added a data_types module for handling different data types
- Added a python based DEServer for testing purposes
- Update the Testing to allow for a real DEServer to be used for testing (#7)
- Add support for `@pytest.mark.server` decorator for tests that require a full DEServer to be running (#7)
- Add a commandline interface for the pydeserver. (#8) Running `pydeserver --port 13241` will start the server on port 13241