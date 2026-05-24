# Air Dashboard Backend

FastAPI backend for station readings, transport matrix generation, and source inversion.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI:
- `/docs`
- `/redoc`

## Notes

- The backend expects:
  - `data/raw/stations.csv`
  - `data/artifacts/final_master_dataset.csv`
- If a timestamp is not provided, the API uses the latest complete snapshot.
