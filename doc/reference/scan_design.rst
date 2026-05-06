.. _scan-design:

#####################
DE-Freescan Design
#####################

This document describes the scanning associated with the DE-Freescan, explaining
its setup, operation, and limitations, along with code examples for properly
interfacing with the scan controller.

The Freescan device drives coils within the microscope — primarily sending voltages
to scan X/Y coils. For each direction (e.g. X), there are four deflection coils
driven: a tilt and detilt coil above the sample, and a tilt and detilt coil below
the sample. These voltages are applied to cancel each other out. In practice, due
to relaxation times within the coils, scan artifacts (scan distortions) and descan
artifacts (probe wandering) can occur.

.. contents:: Table of Contents
   :local:
   :depth: 2

--------------------------
Internal Scan Design
--------------------------

Scan voltages (X/Y) are continuously sent from the DE-Computer to the scan
generator. The scan generator operates in a **FIFO** (First In, First Out) manner,
where scan points are sent to the microscope in the order they are received.
This enables indefinite streaming of scan positions to the microscope.

While this model *could* support continual updates to scan positions, this is
currently not supported due to difficulties with latency, uploading scan patterns
during acquisition, and the dynamic definition of virtual images. As a compromise,
the properties ``Scan - Offset X (points)`` and ``Scan - Offset Y (points)`` can
shift the beam by some fraction of a scan point — analogous to using image shift
for drift correction in a TEM. This is a beta feature that requires additional
testing.

Custom scan patterns may also be defined. In this case, the 3V ↔ −3V area is
subdivided into a grid and only specified positions are scanned. The returned
virtual image will contain the scanned values at those positions and zeros
elsewhere.

--------------------------
Defining Custom Scan Patterns
--------------------------

Lists of X/Y scan points define scan patterns. The total scan area (when no ROI
is active) is defined by the full voltage range of the microscope. Finer voltage
control is achieved by increasing ``Scan - Size X`` and ``Scan - Size Y``.

In most cases, scan patterns are pre-defined (``Raster``, ``Serpentine``,
``Distributed``, etc.) and a single pattern is used. When ``Scan - Repeats`` > 1,
the single scan pattern is repeated continuously into the FIFO buffer.

For custom X/Y scan patterns, it is possible to:

* Send multiple scan patterns and run a selected one by index.
* Cycle through multiple scan patterns in sequence.

.. note::
   The underlying ``height`` and ``width`` must be equal for all patterns in a set.

Example: Sending Multiple Patterns (Scan Repeat == 1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example sends three scan patterns and runs each one individually.

.. tabs::

   .. tab:: Python

      .. code-block:: python

         import numpy as np
         from time import sleep

         scan1 = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])                        # 4 points
         scan2 = np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]])                # 5 points
         scan3 = np.array([[0, 0], [3, 0], [3, 3], [0, 3], [1, 1], [2, 2]])        # 6 points
         scans = [scan3, scan2, scan1]

         client.set_xy_array(scans, height=10, width=10)  # Send all 3 scans to DE-Server

         for i, num_points in enumerate([4, 5, 6]):
             client["Scan - Repeats"] = 1               # Single scan, no repeats
             client["Scan - XY File Pattern ID"] = i    # Select pattern by index
             client["Scan - Enable"] = True
             client.start_acquisition()
             while client.acquiring:
                 sleep(0.1)
             assert client["Scan - Frames (Recorded)"] == num_points  # 4, 5, or 6

   .. tab:: C#

      .. code-block:: csharp

         // TODO: Add C# implementation

   .. tab:: C++

      .. code-block:: cpp

         // TODO: Add C++ implementation

Example: Cycling Through Multiple Patterns (Scan Repeat > 1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example creates five scan patterns derived from a base pattern and cycles
through them for 100 repeats.

.. tabs::

   .. tab:: Python

      .. code-block:: python

         import numpy as np
         from time import sleep

         scan1 = np.array([
             [0, 0], [1, 0], [1, 1], [0, 1],
             [2, 1], [2, 0], [0, 2], [1, 2]
         ])  # 8 points

         scans = [scan1 + 2 * i for i in range(5)]
         client.set_xy_array(scans, height=10, width=10)

         client["Scan - Repeats"] = 100
         client["Scan - Enable"] = True
         client["Scan - Camera Frames Per Point"] = 1
         client["Scan - Repeat Delay"] = 0  # seconds
         client.start_acquisition()
         while client.acquiring:
             sleep(0.1)

         sleep(5)

   .. tab:: C#

      .. code-block:: csharp

         // TODO: Add C# implementation

   .. tab:: C++

      .. code-block:: cpp

         // TODO: Add C++ implementation

Cycling through patterns is important for reducing latency with repeated scans,
particularly with regard to allocating memory for results.

--------------------------
Returning Virtual Images
--------------------------

When ``Scan - Repeats`` > 1 and ``Scan - Repeat Delay (seconds)`` > 5, the camera
will operate continuously: the shutter remains open and the probe moves to the park
position for the duration of the delay. The beam is **not** blanked during this time.

Virtual images are continuously written to disk using a **Ping-Pong buffer** (A → B → A → B …)
that holds the image currently being acquired and the previously completed image.
There are three ways to access virtual images:

1. **Return the "Stitched" Image**
   Returns the current buffer stitched together with the previous buffer, based on
   the current scan position. Primarily used for continuous display purposes.

2. **Return the Last Full Scan**
   Returns the most recently completed full scan image. When buffer A is being
   written to, buffer B is returned, and vice versa. Suitable for fully asynchronous
   workflows where dropping frames is acceptable (e.g. continuous drift correction).

3. **Stream Virtual Images**
   The client subscribes to a stream of images from the server, and every virtual
   image is delivered. Use this when all frames must be captured.

