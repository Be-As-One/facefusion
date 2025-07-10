#!/usr/bin/env python3
"""
FastAPI Handler for FaceFusion Face Swapping
Provides a REST API interface for the FaceFusion face swapping functionality
"""

from fusion_manager import FaceFusionManager, ProcessRequest, ProcessResponse
import uvicorn
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException
import os
import sys
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import logging

# Set environment variables for performance
os.environ.update({
    'OMP_NUM_THREADS': '1',
    'MKL_NUM_THREADS': '1',
    'NUMEXPR_NUM_THREADS': '1'
})

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# FastAPI imports

# Local imports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FastAPI-FaceFusion")


# ============================================================================
# FastAPI Models
# ============================================================================

class ProcessRequestAPI(BaseModel):
    """Face swap processing request for FastAPI"""
    source_url: str = Field(..., description="URL of the source image (face to swap)")
    target_url: str = Field(..., description="URL of the target image/video")
    resolution: str = Field("1024x1024", description="Output resolution")
    model: str = Field("inswapper_128_fp16", description="Face swapper model to use")


class ProcessResponseAPI(BaseModel):
    """Face swap processing response for FastAPI"""
    status: str
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
    job_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    uptime: float
    total_requests: int
    successful_requests: int
    failed_requests: int


# ============================================================================
# FastAPI App
# ============================================================================
# Create manager instance
manager = FaceFusionManager()

# Lifespan context manager for startup/shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app lifecycle"""
    # Startup
    logger.info("Starting FaceFusion FastAPI service...")
    try:
        manager.initialize()
        logger.info(f"Manager initialized: {manager.initialized}")
    except Exception as e:
        logger.error(f"Failed to initialize manager: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    
    # Create output directory
    os.makedirs("outputs", exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down FaceFusion FastAPI service...")

# Create FastAPI app
app = FastAPI(
    title="FaceFusion API",
    description="REST API for FaceFusion face swapping",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "FaceFusion API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "process": "/process",
            "health": "/health",
            "stats": "/stats"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="FaceFusion API",
        version="1.0.0",
        uptime=0,
        total_requests=0,
        successful_requests=0,
        failed_requests=0
    )


@app.post("/process", response_model=ProcessResponseAPI)
async def process_face_swap(request: ProcessRequestAPI):
    """Process a face swap request"""
    if not manager.initialized:
        logger.error("Service not initialized - manager.initialized is False")
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        logger.info(f"Processing request: {request.source_url} -> {request.target_url}")
        
        # Convert FastAPI model to internal model
        internal_request = ProcessRequest(
            source_url=request.source_url,
            target_url=request.target_url,
            resolution=request.resolution,
            model=request.model
        )
        
        result = await manager.process_face_swap(internal_request)
        if result.status == "failed":
            logger.error(f"Processing failed: {result.error}")
            raise HTTPException(status_code=500, detail=result.error)
            
        # Convert internal response to FastAPI model
        return ProcessResponseAPI(
            status=result.status,
            output_path=result.output_path,
            processing_time=result.processing_time,
            error=result.error,
            job_id=result.job_id,
            metadata=result.metadata
        )
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# Error handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Run the FastAPI app
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )