.. _user-agent:

Use of HTTP APIs, caching and the CATS User-agent
=================================================

In order to function CATS makes HTTP based API calls to services
that provide a forecast of future grid carbon intensity and, in
some cases, to attempt to find the physical location of the computer
running CATS (because grid carbon intensity is different in different
locations, even if they are using the same synchronized national power
distribution network). CATS makes use of local caching to minimize the
number of times that these services are used and sets its User-agent
header to help API providers manage their services.

The CATS HTTP User-agent header is::
    
     CATS/version +https://cats.readthedocs.io/
     
where version corresponds to the version number stored in ``cats.__version__``.

For a single user and on a single system CATS will request carbon intensity
information at most once in any half-hour period. This is achieved by setting
the start time embedded in the URL used to request data to the most recent 
half- or whole-hour time. The ``requests_cache`` package then intercepts 
subsequent API calls and returns data without making a new HTTP call to the
carbon intensity service.

CATS only attempts to find the location of the computer where it is running
if the location is not set on the command line or in the configuration file.
In the absence of this information, CATS will make use of the https://ipapi.co/
service, which geolocates the IP address on best-effort basis. These API calls are
also cached.