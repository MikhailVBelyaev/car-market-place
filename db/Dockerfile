FROM postgres:15

# Copy SQL migrations
COPY ./init_db.sql /docker-entrypoint-initdb.d/
COPY ./init_user.sql /docker-entrypoint-initdb.d/
COPY ./updates/*.sql /docker-entrypoint-initdb.d/

# Just keep the JSON dump (used later by Django)
COPY ./dump_cars.json /docker-entrypoint-initdb.d/dump_cars.json