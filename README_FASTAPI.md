# FaceFusion FastAPI Handler

This FastAPI handler provides a REST API interface for the FaceFusion face swapping functionality.

## Features

- REST API endpoints for face swapping
- Support for both image and video processing
- Asynchronous processing
- Health check and statistics endpoints
- File download support for processed outputs
- Configurable resolution and models

## Installation

The required dependencies are already included in `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Start the FastAPI server

```bash
python fastapi_handler.py
```

The server will start on `http://localhost:8000`

### 2. API Endpoints

#### Health Check
```bash
GET /health
```

#### Process Face Swap
```bash
POST /process
Content-Type: application/json

{
    "source_url": "https://example.com/source.jpg",
    "target_url": "https://example.com/target.jpg",
    "resolution": "1024x1024",
    "output_format": "file"
}
```

#### Get Statistics
```bash
GET /stats
```

#### Download Output
```bash
GET /outputs/{filename}
```

### 3. Test the API

Run the test script:
```bash
python test_fastapi.py
```

Or test with curl:
```bash
# Health check
curl http://localhost:8000/health

# Process face swap
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
    "target_url": "https://images.unsplash.com/photo-1494790108755-2616b612b5bc?w=512&h=512&fit=crop&crop=face",
    "resolution": "512x512"
  }'
```

## Configuration

The handler uses the following default configuration:
- Face swapper model: `inswapper_128_fp16`
- Face detector model: `yolo_face`
- Output quality: 80
- Video codec: `libx264`
- Execution providers: `['cuda', 'cpu']`

You can customize these in the `ProcessRequest` parameters.

## API Documentation

When the server is running, visit:
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## Notes

- The API automatically downloads input files from URLs
- Processed outputs are saved in the `outputs/` directory
- Temporary files are automatically cleaned up
- The service initializes FaceFusion on startup
- Supports both CUDA (GPU) and CPU processing