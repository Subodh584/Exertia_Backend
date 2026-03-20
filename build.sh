#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# ONE-TIME: wipe all data and reseed clean
python manage.py flush --no-input
python manage.py seed
