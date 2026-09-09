Place NASA battery files here: B0005.mat, B0006.mat, B0007.mat, B0018.mat, ...

Source: NASA Prognostics Center of Excellence data repository, "Battery Data Set"
(BatteryAgingARC-FY08Q4). The backend loads every *.mat in this folder on
start-up; if the folder is empty it falls back to a synthetic NASA-like
dataset and reports `data_source: synthetic` at GET /api/health.
