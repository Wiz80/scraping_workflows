import requests
import sys
import json
import os

def main(json_file):
    with open(json_file, 'r') as file:
        sites = json.load(file)['sites']

    # Itera sobre los sitios
    for site in sites:
        base_url = site['base_url']
        search_url = site['search_url']
        extract = site['extract']
        
        # Prepara el request
        response = requests.get(f"http://web:8000/discover_and_scrape?base_url={base_url}&search_url={search_url}&extract={extract}")
        
        # Verifica el resultado del request
        if response.status_code == 200:
            print(f"Successfully started scraping for {base_url}")
        else:
            print(f"Failed to start scraping for {base_url}, status code: {response.status_code}")

if __name__ == "__main__":
    # Recibe el archivo JSON como argumento
    json_file = os.getcwd() + "/sites.json"
    main(json_file)
