pyDEServer
===========

Included with the deapi package is a "mock" DE Server that can be used for testing and development purposes.
The pyDEServer is written in Python and is a simple implementation of the DE Server.  The pyDEServer __does not__
fully implement the DE Server API, but it is a good starting point for developing new features or testing existing
features.

The pyDEServer can be started by running the following command:

.. code-block::

    pydeserver --port 13241

Motivation
----------
The DE Server is a complex piece of software and has specific hardware requirements to handle the
data rate and processing requirements of the DE API. The pyDEServer allows developers to test their
code without needing to have access to the DE Server. It also allows for generating
large datastreams for testing purposes with limited hardware/set up requirements. The pyDEServer
should be run on a separate thread and then accessed in the same way as the DE Server.

Acquisitions
------------

The pyDEServer also can "fake" acquisitions. This is useful for testing and development purposes.

During a "Fake" acquisition a timer is started. When functions like
`get_result` are called, the pyDEServer will return the data that would be available at
that time. Additionally, client.acquiring will return True until the timer has finished.

Properties
----------
Properties are initialized from the "prop_dump.json" file. This file is a JSON file that contains some
of the properties that are available on the DE Server.  As certain properties are codependent, those
properties are defined using `sympy` expressions.  This allows certain "Read Only" properties to be updated
automatically when other properties are updated.


Data Creation
-------------

The pyDEServer "Cheats" in a couple of ways:

1. The pyDEServer does not implement the full DE API.  It only implements a subset of the API which means
   that not all the Properties and Methods are implemented. If you are looking for testing a specific feature,
   let us know and we can implement it for you.
2. The pyDEServer fakes data by splitting the data into signal and navigation data. The idea is that the
   navigation data is a set of "n" labels and the signal data is a set of "n" frames. In this way a large
   dataset can be faked by returning the frame n at the index in the navigation data. Programmatically this
   looks like:

.. code-block::

    signal_data = np.random.random((n, 100, 100))
    navigation_data = np.random.random_int(0, n, (10, 10))

    def get_data(index):
        return signal_data[navigation_data[index]]

3. Similarly we can make "Virtual Images" by pre-processing only the few signal frames and returning only the
   points of interest.

This is implemented with the `BaseFakeData` class. Which implements a `__getitem__` method that returns the
data at the index in the navigation data. This can be used to return a single frame or a set of frames.