IRR Explorer
============

# TODO

* exabgp
    * launch
    * feed it config
    * catch STDOUT from the 'run' process

* Investigate issue with records going missing
    * Logging added, so debugging can actually be done

* Database
    * Upgrade to PostgreSQL 9.5.
        * Has better query planner for gin indexes
        * Supports ON CONFLICT (UPSERT) which will save us trouble on mirror updates


