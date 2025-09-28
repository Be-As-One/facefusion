#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from facefusion.face_helper import get_many_faces
from facefusion.vision import read_static_image
import facefusion.globals
from facefusion import state_manager

# Initialize state
state_manager.init_item('face_detector_model', 'yoloface')
state_manager.init_item('face_detector_size', '640x640')
state_manager.init_item('face_detector_score', 0.5)

# Test files
test_files = ['face_1.jpg', 'face_1_update.jpg', 'face_2.jpg', 'face_2_update.webp']

for file_path in test_files:
    if os.path.exists(file_path):
        print(f"\nTesting {file_path}:")
        image = read_static_image(file_path)
        if image is not None:
            print(f"  Image shape: {image.shape}")
            faces = get_many_faces([image])
            if faces:
                print(f"  Detected {len(faces)} face(s)")
                for i, face in enumerate(faces):
                    if hasattr(face, 'bounding_box'):
                        print(f"    Face {i+1}: bbox={face.bounding_box}")
            else:
                print(f"  No faces detected")
        else:
            print(f"  Failed to read image")
    else:
        print(f"\n{file_path}: File not found")