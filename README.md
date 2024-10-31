

https://storage.googleapis.com/for_test_file/%E9%A3%9E%E4%B9%A620240715-170824.mp4

https://storage.googleapis.com/for_test_file/debugger.mp4
https://storage.googleapis.com/for_test_file/debugger.jpeg
PROBABILITY_LIMIT

# python run.py --frame-processors face_swapper face_enhancer -s datasets/source.jpg -t datasets/resized_debugger.jpeg -o  datasets/face-swap999.jpg --headless --face-mask-types occlusion box  --execution-providers cuda

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/datasets/source.jpg -t /facefusion/datasets/target.jpg -o  /facefusion/output.jpg --headless --face-mask-types occlusion box  --execution-providers cuda

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/source.jpg -t /facefusion/debugger.mp4 -o  /facefusion/face-swap.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode many -s /facefusion/source.jpg -t /facefusion/mutil.mp4 -o  /facefusion/face-swap-mutil-many.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode many -s /facefusion/source.jpg -t /facefusion/6min.mp4 -o  /facefusion/face-swap-6min.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/source.jpg -t /facefusion/6min.mp4 -o  /facefusion/face-swap-6min.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode one -s /facefusion/source.jpg -t /facefusion/9s.mp4  -o  /facefusion/face-swap-9s.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode one -s datasets/source.jpg -t datasets/9s.mp4 -o datasets/face-swap-9s.mp4 --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode reference -s datasets/source.jpg -t datasets/test-female.mp4 -o datasets/face-swap-female.mp4 --face-mask-types occlusion box  --face-analyser-gender female --reference-frame-number 457 --execution-providers cuda --headless
# python run.py --reference-frame-number 457  --frame-processors face_swapper face_enhancer --face-selector-mode reference -s datasets/women.jpg -t datasets/test-female.mp4 -o datasets/face-swap-female.mp4 --face-mask-types occlusion box  --face-analyser-gender female --execution-providers cuda --headless

# docker cp facefusion:/facefusion/face-swap-female.mp4 datasets/face-swap-female.mp4


# docker run  -it --name facefusion --rm --gpus all,capabilities=video -p  7860:7860 -v storge:/facefusion/.assets  facefusion:2.6.1 bash


# ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 datasets/resized_debugger.jpeg
# ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 datasets/9s.mp4

# docker run -it --name facefusion --rm --gpus all,capabilities=video -p 7860:7860 -v /mnt/disks/t4/facefusion/datasets:/facefusion/datasets -v storge:/facefusion/.assets  facefusion:2.6.1 bash

# python run.py --frame-processors face_swapper face_enhancer -s /mnt/disks/t4/facefusion/datasets/source.jpg -t /mnt/disks/t4/facefusion/datasets/resized_debugger.jpeg -o  /mnt/disks/t4/facefusion/datasets/face-swap999.jpg --headless --face-mask-types occlusion box  --execution-providers cpu

<!-- facefusion.globals.face_selector_mode -->
# export GOOGLE_APPLICATION_CREDENTIALS="/facefusion/auth.json"
# /usr/bin/supervisord -c /etc/supervisor/conf.d/swapper.conf
# wget https://storage.googleapis.com/for_test_file/%E9%A3%9E%E4%B9%A620240726-164323.mp4 -O datasets/test.mp4
#