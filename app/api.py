from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import polars as pl
import duckdb
import os
from fastapi.responses import StreamingResponse
import io
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the data directory and database path
DATA_DIR = os.path.join(os.getcwd(), "data")
DATABASE_PATH = os.path.join(DATA_DIR, "labeling_data.db")

# Initialize FastAPI
app = FastAPI(title="Labeling Data Export API", version="1.0.0")


@app.get("/export")
async def export_data(
    start_timestamp: Optional[str] = Query(
        None, description="Start timestamp in ISO format"
    ),
    end_timestamp: Optional[str] = Query(
        None, description="End timestamp in ISO format"
    ),
    batch_id: Optional[str] = Query(None, description="Batch ID to filter"),
    batch_name: Optional[str] = Query(None, description="Batch name to filter"),
    output_format: str = Query(
        "csv", description="Output format: csv, json, or parquet"
    ),
):
    try:
        # Validate output format
        if output_format not in {"csv", "json", "parquet"}:
            raise HTTPException(
                status_code=400, detail="Invalid output format specified"
            )

        # Build the query with optional filters
        query = "SELECT * FROM labels WHERE 1=1"
        if start_timestamp:
            query += f" AND timestamp >= '{start_timestamp}'"
        if end_timestamp:
            query += f" AND timestamp <= '{end_timestamp}'"
        if batch_id:
            query += f" AND batch_id = '{batch_id}'"
        if batch_name:
            query += f" AND batch_name = '{batch_name}'"

        logger.info(f"Executing query: {query}")

        # Open the database connection in a context manager
        with duckdb.connect(DATABASE_PATH, read_only=True) as conn:
            df = conn.execute(query).fetchdf()

        if df.empty:
            raise HTTPException(
                status_code=404, detail="No data found for the given filters"
            )

        # Convert the DataFrame to the requested format
        if output_format == "csv":
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=export.csv"},
            )
        elif output_format == "json":
            output = io.StringIO()
            df.to_json(output, orient="records")
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=export.json"},
            )
        elif output_format == "parquet":
            output = io.BytesIO()
            df.to_parquet(output)
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/octet-stream",
                headers={"Content-Disposition": "attachment; filename=export.parquet"},
            )

    except HTTPException as http_exc:
        logger.error(f"HTTP error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
