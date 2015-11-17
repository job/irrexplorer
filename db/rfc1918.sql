BEGIN;
SELECT create_managed_route ('10.0.0.0/8', 'rfc1918');
SELECT create_managed_route ('172.16.0.0/12', 'rfc1918');
SELECT create_managed_route ('192.168.0.0/16', 'rfc1918');
COMMIT;
