#!/bin/sh

# Instalar los requirements
pip install -r requirements.txt

# Ejecutar el flujo de Prefect
/opt/prefect/entrypoint.sh python app/prefect/flows/start_scraping_flow.py
