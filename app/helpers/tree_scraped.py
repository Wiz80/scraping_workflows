import json
from pathlib import Path


class TreeScraped:

    # Función para cargar archivos JSON
    def load_json_file(self, file_path, default_value):
        if Path(file_path).exists():
            try:
                with open(file_path, "r") as json_file:
                    return json.load(json_file)
            except json.JSONDecodeError:
                print(f"Error: El archivo JSON en {file_path} está corrupto o no es válido. Se inicializará con el valor predeterminado.")
                return default_value
        else:
            return default_value  # Debe ser un dict para el archivo de configuración


    def save_json_file(self, file_path, data):
        with open(file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)

    # Función para encontrar un subsite en el JSON
    def find_subsite(self, scraped_sites, site, subsite_value):
        for entry in scraped_sites:
            if entry["site"] == site:
                for subsite in entry["subsites"]:
                    if subsite.get("subsite_value") == subsite_value:
                        return subsite
        return None