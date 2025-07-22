#!/usr/bin/env python3
"""
Simple test script for FaceFusion FastAPI handler
Tests only the core face swap generation functionality
"""

import requests
import time
import sys


def test_face_swap(base_url: str = "http://localhost:8000", resolution: str = "auto"):
    """Test face swap processing
    
    Args:
        base_url: API base URL
        resolution: Output resolution (e.g. '512x512', '1024x1024' or 'auto' for original)
    """
    print("🎭 Testing FaceFusion API face swap...")
    
    # Test data
    test_data = {
        "source_url": "https://cdn.deepswaper.net/deepswaper/before.png",
        # "target_url": "https://storage.googleapis.com/temp-test-file/20250707-190214.mp4",
         "target_url": "https://cdn.deepswaper.net/deepswaper/after.png",
        "resolution": resolution,
        "model": "inswapper_128_fp16"
    }
    
    print(f"Source: {test_data['source_url']}")
    print(f"Target: {test_data['target_url']}")
    print(f"Resolution: {test_data['resolution']}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/process",
            json=test_data,
            timeout=300
        )
        response.raise_for_status()
        result = response.json()
        
        elapsed_time = time.time() - start_time
        
        if result['status'] == 'success':
            print(f"✅ Success! Processing time: {elapsed_time:.2f}s")
            print(f"Job ID: {result.get('job_id')}")
            print(f"Output: {result.get('output_path')}")
            if result.get('metadata'):
                print(f"File type: {result['metadata'].get('file_type')}")
        else:
            print(f"❌ Failed: {result.get('error')}")
            
        return result
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return {"status": "failed", "error": "Timeout"}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"status": "failed", "error": str(e)}


def main():
    """Main test function"""
    base_url = "http://localhost:8000"
    resolution = "auto"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        resolution = sys.argv[2]
    
    print(f"🔗 Testing API at: {base_url}")
    
    # Check if API is running
    try:
        response = requests.get(f"{base_url}/")
        response.raise_for_status()
        api_info = response.json()
        print(f"✅ API running: {api_info['service']} v{api_info['version']}")
    except Exception as e:
        print(f"❌ Cannot connect to API: {str(e)}")
        print("💡 Start API with: python fastapi_handler.py")
        return
    
    # Run face swap test
    print("\n" + "="*50)
    result = test_face_swap(base_url, resolution)
    print("="*50)
    print(f"Test result: {result['status']}")
    
    if len(sys.argv) == 1:
        print("\n💡 Usage: python test_fastapi.py [base_url] [resolution]")
        print("   resolution can be 'auto', '512x512', '1024x1024', etc.")


if __name__ == "__main__":
    main()