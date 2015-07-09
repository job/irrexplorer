IRR Explorer
============

[![Build Status](https://travis-ci.org/job/irrexplorer.svg?branch=master)](https://travis-ci.org/job/irrexplorer)
[![Coverage Status](https://coveralls.io/repos/job/irrexplorer/badge.svg?branch=master)](https://coveralls.io/r/job/irrexplorer?branch=master)

Explore IRR & BGP data in near real time
----------------------------------------

<p align="center">
    <img src="https://raw.githubusercontent.com/job/irrexplorer/master/docs/irrexplorer-logo.png" />
</p>

Background
----------

IRR Explorer was written to make it easier to debug data in the IRR
system. An example is to verify whether you would be impacted by deployment
if filtering strategies such as "IRR Lockdown".

video: https://ripe70.ripe.net/archives/video/21/
pdf: https://ripe70.ripe.net/presentations/52-RIPE70_jobsnijders_irrlockdown.pdf


Setup
-----

Edit db/irr.yml to your liking.

Note that mirroring of many IRR databases is not possible without getting
access granted.

```
( cd db ; ./bootstrap )
```
This will take download IRR dumps and setup the databases. It will take some time.

Continously updating BGP and IRR sources:
```
create_worksh > work.sh
chmod +x work.sh
./work.sh
```

Finally start the web interface
```
./irexwww
```

There is query tool as well:
```
./query 1.2.3.0/24
```
It is rather basic and need some work though.

