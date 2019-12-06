# Python Scripts for Interacting with BPM Firmware

These scripts require CPSW and its 'pycpsw' wrapper
for python.

## bpmSimInit.py

This 'driver' script can be used to initialize the
BPM firmware and in particular, the simulator.

Prior to executing this script the 'defaults.yaml'
that is distributed with the firmware image should
be loaded to do basic initialization.

## LinSim.py
The classes and routines defined in this file are
designed to program the filter coefficients of the
BPM simulator.

Starting with a standard description of a linear system
(e.g., as a transfer function) the `LinSys` class
transforms the system into a parallel representation
of complex single-order (class `firstOrderSys`) sub-systems.

The single-order systems are expanded with additional,
cancelling pole/zero pairs to obtain a representation
that permits a pipelined implementation.

Further transformations are applied to extract coefficients
that are suitable for the particular firmware implementation
(this includes conversion into the proper 18-bit fixed-point
representation etc.).

Two wrappers `mkCavitySystem` and `mkStriplineSystem` are
available which compute appropriate linear systems and
simulator coefficients from high-level parameters such as
cavity center-frequencies and Qs.

`mkStriplineSystem` synthesizes 4'th order Chebyshev
band-pass filters from a given center-frequency and bandwidth,
one for each stripline channel. The individual center-frequencies
are slightly randomized ("tolerance") around the specified value.

The frequences should be normalized to the sampling frequency.

    mkStriplineSystem( fo_f = 300/370, bw_f = 40/370 )

`mkCavitySystem` behaves exactly like its stripline counterpart
but in addition to the band-pass filter it features a second-
order resonator for simulating the cavity response. The center
frequency and Q of the cavity can be specified individually for
each channel.

    Fcav = [0, 38.2/fs , 30.3/fs  , 37.2/fs ]
    Qcav = [0, 38.2/2.1, 30.3/1.25, 37.2/3.3]
    Fflt = 35/370
    Bflt = 30/370
    mkCavitySystem( [ 0, 28.5/370, 28.8/370, 29/370 ], [ 0, 73, 68, 50 ]

## bpm.py
This script defines the `SIM` class which interfaces to the
registers of the simulator. E.g., it has methods to start/stop
the simulator or download coefficients without the user having
to remember the register names etc.

## loadYaml.py
Utility class to load a firmware-description YAML file as specified
on the command line (-Y option) as well as tweaking the board's IP
address.

## pathGrep.py
Utility to scan the device description for patterns (using
standard regex). This makes it easier to locate registers
without having to remember the full path name.

## bpmMiscUtils.py
Several utility classes for interacting with CPSW ScalVals.
E.g., the `SVL` class automatically creates ScalVal interfaces
for all children of a hub (device). The user may then interact
(get/set) with individual registers by using their name:

    mydev.set("registerX", 44)
