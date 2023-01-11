#!/bin/bash
#
# Query Mastodon's database and look for newly created apps
#

POSTGRES="docker exec postgres psql -U postgres -d mastodon"

# Who are we emailing?
DEST="me@example.invalid"


# Run the query
RESP=`$POSTGRES -c "SELECT id, name, redirect_uri, scopes, created_at, updated_at, superapp, website FROM public.oauth_applications WHERE created_at > now() - interval '24 hour' "`

# Any results?
if [ "`echo "${RESP}" | tail -n1`" == "(0 rows)" ]
then
    # No results
    exit
fi

# Send a mail
cat << EOM | mail -s "New Mastodon apps registered on $HOSTNAME" $DEST
Greetings

Newly registered apps have been seen in the Mastodon database on $HOSTNAME

$RESP


You can extract additional information on each of these by taking the ID and running

    SELECT * FROM public.oauth_applications WHERE id=<id>

In Postgres

EOM

