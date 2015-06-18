-- Database scheme for IRRExplorer
-- Tied to PostgreSQL due to use of cidr type and gist indexing,
-- to effeciently query routes.
--
-- Requires PostgreSQL 9.4 (gist indexing of cidr/inet)


CREATE TABLE sources (
    id          serial              NOT NULL PRIMARY KEY,
    name        text                UNIQUE NOT NULL
);

CREATE TABLE managed_routes (
    route       cidr                NOT NULL,
    source_id   integer             NOT NULL REFERENCES sources(id)
);


CREATE VIEW managed_routes_view AS
    SELECT
        route, name AS source
    FROM
        managed_routes LEFT OUTER JOIN sources ON (managed_routes.source_id = sources.id);


-- consider expanding this with start/end timestamp later
CREATE TABLE routes (
    route       cidr                NOT NULL,
    asn         integer             NOT NULL,
    source_id   integer             NOT NULL REFERENCES sources(id),

    -- The unique constraint may not be the best from an efficiancy point of view,
    -- but having duplicates is likely to cause weird results
    CONSTRAINT unique_entry UNIQUE (route, asn, source_id),
    CONSTRAINT positive_asn CHECK (asn > 0)
);

CREATE INDEX route_gist ON routes USING gist (route inet_ops);

CREATE VIEW routes_view AS
    SELECT
        route, asn, name AS source
    FROM routes LEFT OUTER JOIN sources ON (routes.source_id = sources.id);


CREATE TABLE as_sets (
    as_macro    text                NOT NULL,
    members     text[]              NOT NULL,
    source_id   integer             NOT NULL REFERENCES sources(id),

    CONSTRAINT unique_macro_source UNIQUE (as_macro, source_id)
);


CREATE VIEW as_sets_view AS
    SELECT
        as_macro, members, name AS source
    FROM as_sets LEFT OUTER JOIN sources ON (as_sets.source_id = sources.id);



CREATE OR REPLACE FUNCTION create_managed_route (
    in_route                cidr,
    in_source               varchar
)
RETURNS integer AS $inserted$

DECLARE
    source_id               integer;
    result                  integer;
BEGIN
    -- check if we have source, create if not
    SELECT sources.id INTO source_id FROM sources WHERE name = in_source;
    IF NOT FOUND THEN
        INSERT INTO sources (name) VALUES (in_source) RETURNING id INTO source_id;
    END IF;

    INSERT INTO managed_routes (route, source_id) VALUES (in_route, source_id);

    result = 1;
    return result;
END;
$inserted$
LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION create_route (
    in_route                cidr,
    in_asn                  integer,
    in_source               varchar
)
RETURNS integer AS $inserted$

DECLARE
    source_id               integer;
    result                  integer;
BEGIN
    -- check if we have source, create if not
    SELECT sources.id INTO source_id FROM sources WHERE name = in_source;
    IF NOT FOUND THEN
        INSERT INTO sources (name) VALUES (in_source) RETURNING id INTO source_id;
    END IF;

    INSERT INTO routes (route, asn, source_id) VALUES (in_route, in_asn, source_id);

    result = 1;
    return result;
END;
$inserted$
LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION create_as_set (
    in_as_macro             text,
    in_members              text[],
    in_source               varchar
)
RETURNS integer AS $inserted$

DECLARE
    source_id               integer;
    result                  integer;
BEGIN
    -- check if we have source, create if not
    SELECT sources.id INTO source_id FROM sources WHERE name = in_source;
    IF NOT FOUND THEN
        INSERT INTO sources (name) VALUES (in_source) RETURNING id INTO source_id;
    END IF;

    INSERT INTO as_sets (as_macro, members, source_id) VALUES (in_as_macro, in_members, source_id);

    result = 1;
    return result;
END;
$inserted$
LANGUAGE plpgsql;

