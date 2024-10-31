import subprocess
import sys
import pytest

from facefusion.download import conditional_download


@pytest.fixture(scope = 'module', autouse = True)
def before_all() -> None:
	conditional_download('.assets/examples',
	[
		'https://github.com/facefusion/facefusion-assets/releases/download/examples/source.jpg',
		'https://github.com/facefusion/facefusion-assets/releases/download/examples/target-240p.mp4'
	])
	subprocess.run([ 'ffmpeg', '-i', '.assets/examples/target-240p.mp4', '-vframes', '1', '.assets/examples/target-240p.jpg' ])


def test_swap_face_to_image() -> None:
	commands = [ sys.executable, 'run.py', '--frame-processors', 'face_swapper', '-s', '.assets/examples/source.jpg', '-t', '.assets/examples/target-240p.jpg', '-o', '.assets/examples/test_swap_face_to_image.jpg', '--headless' ]
	run = subprocess.run(commands, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)

	assert run.returncode == 0
	assert 'image succeed' in run.stdout.decode()


def test_swap_face_to_video() -> None:
	commands = [ sys.executable, 'run.py', '--frame-processors', 'face_swapper', '-s', '.assets/examples/source.jpg', '-t', '.assets/examples/target-240p.mp4', '-o', '.assets/examples/test_swap_face_to_video.mp4', '--trim-frame-end', '10', '--headless' ]
	run = subprocess.run(commands, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)

	assert run.returncode == 0
	assert 'video succeed' in run.stdout.decode()

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/source.jpg -t /facefusion/resized_debugger.jpeg -o  /facefusion/face-swap8.jpg --headless --face-mask-types occlusion box  --execution-providers cuda

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/source.jpg -t /facefusion/target.jpg -o  /facefusion/output.jpg --headless --face-mask-types occlusion box  --execution-providers cuda

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/source.jpg -t /facefusion/debugger.mp4 -o  /facefusion/face-swap.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode many -s /facefusion/source.jpg -t /facefusion/mutil.mp4 -o  /facefusion/face-swap-mutil-many.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode many -s /facefusion/source.jpg -t /facefusion/6min.mp4 -o  /facefusion/face-swap-6min.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer -s /facefusion/source.jpg -t /facefusion/6min.mp4 -o  /facefusion/face-swap-6min.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

# python run.py --frame-processors face_swapper face_enhancer --face-selector-mode one -s /facefusion/source.jpg -t /facefusion/9s.mp4  -o  /facefusion/face-swap-9s.mp4  --face-mask-types occlusion box  --execution-providers cuda --headless

#  --face-mask-regions skin left-eyebrow right-eyebrow left-eye right-eye glasses nose mouth upper-lip lower-lip

