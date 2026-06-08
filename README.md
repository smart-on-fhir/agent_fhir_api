# agent-fhir-api

A small Flask-based FHIR extractor API for reading ndjson FHIR resources and returning paginated results.

## Setup

### Requirements
- Python 3.14 or newer
- UV 0.11.2 or newer

### Install dependencies

From the repository root:

```bash
uv sync
source .venv/bin/activate
```

### Data directory

The service expects a directory of FHIR ndjson files. By default it uses:

```bash
../sample-bulk-fhir-datasets/500-patients/
```

You can override this location by setting the `FHIR_DIR` environment variable before starting the API. Datasets can be generate using `https://github.com/smart-on-fhir/sample-bulk-fhir-datasets`

## Start

Run the API from the project root:

```bash
python api.py
```

This starts the Flask development server on `http://127.0.0.1:5000`.

## Usage

### 1. Request a resource type

```bash
curl -X POST http://127.0.0.1:5000/fhir/Patient/ \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 2. Request a resource type for specific patients

```bash
curl -X POST http://127.0.0.1:5000/fhir/ExplanationOfBenefit/ \
  -H "Content-Type: application/json" \
  -d '{"patients": ["Patient/1", "Patient/2"]}'
```

### 3. Request a resource type and filter returned fields

```bash
curl -X POST http://127.0.0.1:5000/fhir/Observation/ \
  -H "Content-Type: application/json" \
  -d '{"patients": ["Patient/1"], "fields": ["id", "status", "code"]}'
```

### 4. Request a paginated page of results

```bash
curl -X POST 'http://127.0.0.1:5000/fhir/Condition/?_offset=10&_count=5' \
  -H "Content-Type: application/json" \
  -d '{"patients": ["Patient/1"]}'
```

