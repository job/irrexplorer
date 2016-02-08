IRR Explorer
============

# TODO

* exabgp
    * launch
    * feed it config
    * catch STDOUT from the 'run' process

* BGP/NRTM worker
    * Integrated into a single exacutable (work.sh is messy)

* Database
    * Upgrade to PostgreSQL 9.5.
        * Has better query planner for gin indexes
        * Supports ON CONFLICT (UPSERT) which will save us trouble on mirror updates


