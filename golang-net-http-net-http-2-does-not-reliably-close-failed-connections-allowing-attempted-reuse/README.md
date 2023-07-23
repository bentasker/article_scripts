# Go Dead Connection Re-use

Used to help provide a repro in [Golang HTTP/2 connections can become blocked for extremely long periods of time](https://www.bentasker.co.uk/posts/blog/software-development/golang-net-http-net-http-2-does-not-reliably-close-failed-connections-allowing-attempted-reuse.html).

The Go Code simply places requests, in a loop, you'll need to follow additional repro steps [detailed here](https://www.bentasker.co.uk/posts/blog/software-development/golang-net-http-net-http-2-does-not-reliably-close-failed-connections-allowing-attempted-reuse.html#repro).

----

### Files

- [repro](repro/): Initial repro script
- [dirty_hack](dirty_hack/): Using a nasty hack to mitigate
- [with_healthchecks](with_healthchecks/): Using H2 healthchecks to mitigate
- [check_upstream_h2_ping_support.py](check_upstream_h2_ping_support.py): Python script to check if a server supports HTTP/2 Pings

----
### License

Copyright (c) B Tasker, 2023. Released under a [BSD 3-Clause License](https://www.bentasker.co.uk/pages/licenses/bsd-3-clause.html)

