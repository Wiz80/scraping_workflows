from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
from app.tasks.scraping_task import start_scraping_tasks
from app.tasks.urls_discover import discover_urls

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

with DAG(
    'scraping_workflow',
    default_args=default_args,
    description='A simple scraping DAG',
    schedule_interval=None,
) as dag:

    discover_urls_task = PythonOperator(
        task_id='discover_urls',
        python_callable=discover_urls,
        op_args=['https://arxiv.org', '/search/?query=AI'],
    )

    scrape_sites_task = PythonOperator(
        task_id='scrape_sites',
        python_callable=start_scraping_tasks,
        op_args=['https://arxiv.org'],
    )

    discover_urls_task >> scrape_sites_task
