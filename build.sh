#!/usr/bin/env bash
# Script de build usado pelo Render (veja render.yaml).
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py populate_termos

# Cria o administrador na primeira implantação, se as variáveis estiverem definidas no Render.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input || echo "Administrador já existe, seguindo."
fi
