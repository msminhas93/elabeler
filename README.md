## elabeler: NLP Text Labeling Tool
elabeler is an NLP text labeling tool that enables  easy labeling of text data. It features a Streamlit frontend and a FastAPI backend for exporting labeled data. This tool is designed to help users efficiently upload, label, and manage the labels.
### Features
- Streamlit Frontend: An intuitive interface for uploading CSV files, labeling text data, and managing labels.
- FastAPI Backend: An API for exporting labeled data with filtering options based on timestamps, batch IDs, and batch names.
- Single File Upload: Users can upload one CSV file at a time, ensuring a clean and organized labeling process.
- Export Options: Export labeled data in multiple formats, including CSV, JSON, and Parquet.

### Directory Structure

```
├── Dockerfile.fastapi
├── Dockerfile.streamlit
├── app
│   ├── __init__.py
│   ├── api.py
│   ├── labeling_app.py
│   └── requirements.txt
├── data
│   └── labeling_data.db
├── docker-compose.yml
├── readme.md
└── tests
    ├── __init__.py
    ├── conftest.py
    └── test_api.py
```
### Prerequisites
- Docker
- Docker Compose

### Setup and Installation
1. Clone the Repository: 
   ```
   git clone https://github.com/msminhas93/elabeler.git
   cd elabeler
   ```
2. Build and Run with Docker Compose:
   ```
   docker-compose up --build
   ```
3. Access the Services:
   - Streamlit app: http://localhost:8501
   - FastAPI app: http://localhost:8000

### Usage

#### Streamlit App
- Upload CSV: Upload a CSV file containing text data.
- Label Texts: Use the interface to label each text entry.
- Navigate Pages: Use the navigation buttons to switch between pages of data.
- Export Data: Export labeled data in CSV, JSON, or Parquet format.
#### FastAPI API
The FastAPI service provides an endpoint to export labeled data with optional filtering:
- Endpoint: /export
- Query Parameters:
   - start_timestamp: Filter by start timestamp (ISO format).
   - end_timestamp: Filter by end timestamp (ISO format).
   - batch_id: Filter by batch ID.
   - batch_name: Filter by batch name.
   - output_format: Specify the output format (csv, json, parquet).

##### Example request:
```
curl "http://localhost:8000/export?output_format=json"
```

### Testing
1. Install Testing Dependencies: 
   
   Ensure pytest and httpx are installed:
   ```
   pip install pytest httpx
   ```
### Run Tests:
1. Execute the tests using pytest:

   ```
   pytest tests/
   ```


### Contributing
Contributions are welcome! Please submit a pull request or open an issue for any improvements or bug fixes.