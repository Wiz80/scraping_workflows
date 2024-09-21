# scrape_runner.py

import argparse
import asyncio
from app.helpers.urls_discover import discover_urls
from app.helpers.scraping_task import start_scraping_tasks

def parse_arguments():
    parser = argparse.ArgumentParser(description='Script para descubrir y scrapear URLs.')

    # Argumentos para discover_urls
    parser.add_argument('--base_url', '-b', required=True, help='Base URL del sitio web.')
    parser.add_argument('--search_url', '-s', required=False, help='URL de búsqueda para descubrir URLs.')
    parser.add_argument('--extract', '-e', required=True, help='Tipo de extracción (e.g., keyword en href).')
    parser.add_argument('--pagination', '-p', action='store_true', help='Habilitar paginación.')
    parser.add_argument('--provided_urls', '-u', nargs='*', help='URLs proporcionadas para scrapear.')

    # Argumentos para start_scraping_tasks
    parser.add_argument('--subsite_key', '-k', required=False, help='Clave del subsite.')
    parser.add_argument('--subsite_value', '-v', required=False, help='Valor del subsite.')
    parser.add_argument('--extract_type', '-x', required=False, help='Tipo de extracción para scraping (pdf o page).')

    args = parser.parse_args()
    return args

async def main():
    args = parse_arguments()

    base_url = args.base_url
    search_url = args.search_url if args.search_url else base_url
    extract = args.extract
    pagination = args.pagination
    provided_urls = args.provided_urls if args.provided_urls else []

    # Construir diccionario de subsites
    subsites = {}
    if args.subsite_key and args.subsite_value:
        subsites[args.subsite_key] = args.subsite_value

    # Paso 1: Descubrir URLs
    print("Iniciando descubrimiento de URLs...")
    num_discovered = await discover_urls(
        base_url=base_url,
        search_url=search_url,
        subsites=subsites,
        extract=extract,
        pagination=pagination,
        provided_urls=provided_urls
    )
    print(f"Descubrimiento completado. URLs descubiertas: {num_discovered}")

    # Paso 2: Iniciar Scraping
    print("Iniciando scraping de URLs...")
    extract_type = args.extract_type if args.extract_type else 'page'
    success = await start_scraping_tasks(
        base_url=base_url,
        extract=extract_type,
        subsites=subsites
    )
    if success:
        print("Scraping completado exitosamente.")
    else:
        print("Scraping completado con errores.")

if __name__ == "__main__":
    asyncio.run(main())
