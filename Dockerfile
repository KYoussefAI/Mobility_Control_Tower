FROM apache/airflow:2.10.5-python3.11

WORKDIR /opt/mct
COPY --chown=airflow:root . /opt/mct
RUN pip install --no-cache-dir ".[analytics]"

ENV MCT_DATA_ROOT=/opt/mct/data \
    MCT_DBT_DATABASE_PATH=/opt/mct/data/mart/mobility_control_tower.duckdb \
    AIRFLOW__CORE__DAGS_FOLDER=/opt/mct/airflow/dags \
    AIRFLOW__CORE__LOAD_EXAMPLES=False

