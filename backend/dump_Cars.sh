#!/bin/bash
set -e

# Go to Django backend directory
cd "$(dirname "$0")"


# Dump only "cars.Car" model data into a JSON file
python manage.py dumpdata cars.Car --indent 2 > ../db/dump_cars.json
