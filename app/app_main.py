from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import requests
import os
import uuid
from dotenv import load_dotenv
from app.helpers.urls_discover import discover_urls
from app.helpers.scraping_task import start_scraping_tasks
from app.helpers.queue_manager import add_queue



load_dotenv()
AIRFLOW_API_URL = os.getenv('AIRFLOW_API_URL')
AIRFLOW_USERNAME = os.getenv('AIRFLOW_USERNAME')
AIRFLOW_PASSWORD = os.getenv('AIRFLOW_PASSWORD')


app = FastAPI()


class ScrapePayload(BaseModel):
    base_url: str
    urls: Optional[List[str]] = []
    scrape_type: str 

@app.post("/start_scraping")
async def start_scraping(payload: ScrapePayload):
    try:
        # Lógica para ejecutar el DAG de Airflow llamando al discovery y luego a RabbitMQ
        dag_trigger_url = os.getenv('AIRFLOW_DAG_TRIGGER_URL')
        
        # Payload para el DAG
        dag_payload = {
            "base_url": payload.base_url,
            "urls": payload.urls,
            "scrape_type": payload.scrape_type
        }

        # Llamar al DAG en Airflow
        response = requests.post(
            dag_trigger_url,
            json=dag_payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Error triggering DAG: {response.text}")

        return {"message": "DAG triggered successfully", "dag_run_id": response.json().get('dag_run_id')}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/discover")
async def discover(payload: ScrapePayload):
    base_url = payload.base_url
    extract = payload.scrape_type
    provided_urls = payload.urls
    
    queue_name = f"url_queue_{uuid.uuid4()}"
    
    try:
        add_queue(base_url=base_url, queue_name=queue_name)
        
        # Llamar a discover_urls para enviar URLs a la cola específica
        num_urls = await discover_urls(
            base_url=base_url, 
            search_url=base_url, 
            subsites={}, 
            extract=extract, 
            pagination=False, 
            rabbitmq_queue=queue_name,
            provided_urls=provided_urls
        )
        
        return {"message": "URLs discovery completed", "num_urls": num_urls, "queue_name": queue_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QueryParams(BaseModel):
    query: str

@app.post("/discover_arxiv")
async def discover_arxiv(query_params: QueryParams):
    query = query_params.query
    
    search_url = f'https://arxiv.org/search/?searchtype=all&query={query}&abstracts=show&size=200&order=-announced_date_first'
    subsites = {"query": query}

    try:
        
        num_urls = await discover_urls(base_url='https://arxiv.org', 
                                       search_url=search_url, 
                                       subsites=subsites, 
                                       extract='pdf', 
                                       pagination=False, 
                                       rabbitmq_queue='url_queue')
        
        return {"message": "URLs discovery completed", "num_urls": num_urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/trigger_arxiv_discover")
async def trigger_arxiv_discover(params: QueryParams):
    try:
        # Payload que incluye la configuración (conf) con el parámetro query
        payload = {
            "conf": {
                "query": params.query
            }
        }
        # Hacer la petición a la API de Airflow
        response = requests.post(AIRFLOW_API_URL, json=payload, auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD))

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error triggering DAG: {response.text}")

        return {"message": "DAG triggered successfully", "query": params.query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ScrapingRequest(BaseModel):
    base_url: str
    subsites: Optional[Dict[str, str]] = None
    extract: str
    query: str

class ScrapingResponse(BaseModel):
    status: str
    data: str = None
    message: str = None


@app.post("/start-scraping", response_model=ScrapingResponse)
async def start_scraping(request: ScrapingRequest):
    try:
        subsites = request.subsites or {}
        if "query" not in subsites:
            subsites["query"] = request.query

        result = await start_scraping_tasks(
            base_url=request.base_url,
            subsites=subsites,
            extract=request.extract
        )
        return {"status":200, "data": "Succesfully Scraped Sites", "message":result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/trigger_discover")
async def trigger_discover(payload: ScrapePayload):

    DAG_URL = f"{AIRFLOW_API_URL}/discover_and_scrape_dag/dagRuns"
    base_url = payload.base_url
    extract = payload.scrape_type
    provided_urls = payload.urls if payload.urls else []

    queue_name = f"url_queue_{uuid.uuid4()}"

    try:
        add_queue(
            base_url=base_url,
            queue_name=queue_name,
            pending_urls=provided_urls.copy()
        )

        num_urls = await discover_urls(
            base_url=base_url,
            search_url=base_url,
            subsites={},
            extract=extract,
            pagination=False,
            rabbitmq_queue=queue_name,
            provided_urls=provided_urls
        )

        # Enviar una solicitud para ejecutar el DAG en Airflow
        dag_run_payload = {
            "conf": {
                "base_url": base_url,
                "urls": provided_urls,
                "extract": extract
            }
        }

        # Trigger el DAG usando la API de Airflow
        airflow_response = requests.post(
            DAG_URL,
            json=dag_run_payload,
            auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD)
        )

        if airflow_response.status_code not in [200, 201]:
            raise HTTPException(status_code=500, detail=f"Error triggering DAG: {airflow_response.text}")

        return {
            "message": "DAG triggered successfully",
            "extract": extract,
            "queue_name": queue_name,
            "num_urls": num_urls
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Levantar el servidor FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)
