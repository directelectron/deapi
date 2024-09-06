.. _changelog:

Changelog
*********

This document describes the changes in the DEAPI library.


Unreleased
==========
- Initial release
- Renamed `Client` functions from CamelCase to snake_case (Legacy functions are still available)
- Added buffer_protocol module for handling different buffer protocol files
- Added a data_types module for handling different data types
- Added a python based DEServer for testing purposes
- Update the Testing to allow for a real DEServer to be used for testing (#7)
- Add support for `@pytest.mark.server` decorator for tests that require a full DEServer to be running (#7)
- Add a commandline interface for the pydeserver. (#8) Running `pydeserver --port 13241` will start the server on port 13241