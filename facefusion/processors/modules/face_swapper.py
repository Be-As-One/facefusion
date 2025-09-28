import os
from argparse import ArgumentParser
from functools import lru_cache
from typing import List, Tuple

import cv2
import numpy

import facefusion.choices
import facefusion.jobs.job_manager
import facefusion.jobs.job_store
import facefusion.processors.core as processors
from facefusion import config, content_analyser, face_classifier, face_detector, face_landmarker, face_masker, face_recognizer, inference_manager, logger, process_manager, state_manager, video_manager, wording
from facefusion.common_helper import get_first
from facefusion.download import conditional_download_hashes, conditional_download_sources, resolve_download_url
from facefusion.execution import has_execution_provider
from facefusion.face_analyser import get_average_face, get_many_faces, get_one_face
from facefusion.face_helper import paste_back, warp_face_by_face_landmark_5
from facefusion.face_masker import create_area_mask, create_box_mask, create_occlusion_mask, create_region_mask
from facefusion.face_selector import find_similar_faces, sort_and_filter_faces, sort_faces_by_order, compare_faces
from facefusion.face_store import get_reference_faces
from facefusion.filesystem import filter_image_paths, has_image, in_directory, is_image, is_video, resolve_relative_path, same_file_extension
from facefusion.model_helper import get_static_model_initializer
from facefusion.processors import choices as processors_choices
from facefusion.processors.pixel_boost import explode_pixel_boost, implode_pixel_boost
from facefusion.processors.types import FaceSwapperInputs
from facefusion.program_helper import find_argument_group
from facefusion.thread_helper import conditional_thread_semaphore
from facefusion.types import ApplyStateItem, Args, DownloadScope, Embedding, Face, InferencePool, ModelOptions, ModelSet, ProcessMode, QueuePayload, UpdateProgress, VisionFrame, FaceMapping, FaceMappingList
from facefusion.vision import read_image, read_static_image, read_static_images, unpack_resolution, write_image


@lru_cache(maxsize = None)
def create_static_model_set(download_scope : DownloadScope) -> ModelSet:
	return\
	{
		'blendswap_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'blendswap_256.hash'),
					'path': resolve_relative_path('../.assets/models/blendswap_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'blendswap_256.onnx'),
					'path': resolve_relative_path('../.assets/models/blendswap_256.onnx')
				}
			},
			'type': 'blendswap',
			'template': 'ffhq_512',
			'size': (256, 256),
			'mean': [ 0.0, 0.0, 0.0 ],
			'standard_deviation': [ 1.0, 1.0, 1.0 ]
		},
		'ghost_1_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_1_256.hash'),
					'path': resolve_relative_path('../.assets/models/ghost_1_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_1_256.onnx'),
					'path': resolve_relative_path('../.assets/models/ghost_1_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.onnx')
				}
			},
			'type': 'ghost',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'ghost_2_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_2_256.hash'),
					'path': resolve_relative_path('../.assets/models/ghost_2_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_2_256.onnx'),
					'path': resolve_relative_path('../.assets/models/ghost_2_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.onnx')
				}
			},
			'type': 'ghost',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'ghost_3_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_3_256.hash'),
					'path': resolve_relative_path('../.assets/models/ghost_3_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_3_256.onnx'),
					'path': resolve_relative_path('../.assets/models/ghost_3_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.onnx')
				}
			},
			'type': 'ghost',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'hififace_unofficial_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.1.0', 'hififace_unofficial_256.hash'),
					'path': resolve_relative_path('../.assets/models/hififace_unofficial_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.1.0', 'arcface_converter_hififace.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_hififace.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.1.0', 'hififace_unofficial_256.onnx'),
					'path': resolve_relative_path('../.assets/models/hififace_unofficial_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.1.0', 'arcface_converter_hififace.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_hififace.onnx')
				}
			},
			'type': 'hififace',
			'template': 'mtcnn_512',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'hyperswap_1a_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1a_256.hash'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1a_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1a_256.onnx'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1a_256.onnx')
				}
			},
			'type': 'hyperswap',
			'template': 'arcface_128',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'hyperswap_1b_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1b_256.hash'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1b_256.hash')
				}
			},
			'sources':
				{
					'face_swapper':
					{
						'url': resolve_download_url('models-3.3.0', 'hyperswap_1b_256.onnx'),
						'path': resolve_relative_path('../.assets/models/hyperswap_1b_256.onnx')
					}
				},
			'type': 'hyperswap',
			'template': 'arcface_128',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'hyperswap_1c_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1c_256.hash'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1c_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1c_256.onnx'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1c_256.onnx')
				}
			},
			'type': 'hyperswap',
			'template': 'arcface_128',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		},
		'inswapper_128':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128.hash'),
					'path': resolve_relative_path('../.assets/models/inswapper_128.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128.onnx'),
					'path': resolve_relative_path('../.assets/models/inswapper_128.onnx')
				}
			},
			'type': 'inswapper',
			'template': 'arcface_128',
			'size': (128, 128),
			'mean': [ 0.0, 0.0, 0.0 ],
			'standard_deviation': [ 1.0, 1.0, 1.0 ]
		},
		'inswapper_128_fp16':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128_fp16.hash'),
					'path': resolve_relative_path('../.assets/models/inswapper_128_fp16.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128_fp16.onnx'),
					'path': resolve_relative_path('../.assets/models/inswapper_128_fp16.onnx')
				}
			},
			'type': 'inswapper',
			'template': 'arcface_128',
			'size': (128, 128),
			'mean': [ 0.0, 0.0, 0.0 ],
			'standard_deviation': [ 1.0, 1.0, 1.0 ]
		},
		'simswap_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_256.hash'),
					'path': resolve_relative_path('../.assets/models/simswap_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_256.onnx'),
					'path': resolve_relative_path('../.assets/models/simswap_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.onnx')
				}
			},
			'type': 'simswap',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': [ 0.485, 0.456, 0.406 ],
			'standard_deviation': [ 0.229, 0.224, 0.225 ]
		},
		'simswap_unofficial_512':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_unofficial_512.hash'),
					'path': resolve_relative_path('../.assets/models/simswap_unofficial_512.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_unofficial_512.onnx'),
					'path': resolve_relative_path('../.assets/models/simswap_unofficial_512.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.onnx')
				}
			},
			'type': 'simswap',
			'template': 'arcface_112_v1',
			'size': (512, 512),
			'mean': [ 0.0, 0.0, 0.0 ],
			'standard_deviation': [ 1.0, 1.0, 1.0 ]
		},
		'uniface_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'uniface_256.hash'),
					'path': resolve_relative_path('../.assets/models/uniface_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'uniface_256.onnx'),
					'path': resolve_relative_path('../.assets/models/uniface_256.onnx')
				}
			},
			'type': 'uniface',
			'template': 'ffhq_512',
			'size': (256, 256),
			'mean': [ 0.5, 0.5, 0.5 ],
			'standard_deviation': [ 0.5, 0.5, 0.5 ]
		}
	}


def get_inference_pool() -> InferencePool:
	model_names = [ get_model_name() ]
	model_source_set = get_model_options().get('sources')

	return inference_manager.get_inference_pool(__name__, model_names, model_source_set)


def clear_inference_pool() -> None:
	model_names = [ get_model_name() ]
	inference_manager.clear_inference_pool(__name__, model_names)


def get_model_options() -> ModelOptions:
	model_name = get_model_name()
	return create_static_model_set('full').get(model_name)


def get_model_name() -> str:
	model_name = state_manager.get_item('face_swapper_model')

	if has_execution_provider('coreml') and model_name == 'inswapper_128_fp16':
		return 'inswapper_128'
	return model_name


def register_args(program : ArgumentParser) -> None:
	group_processors = find_argument_group(program, 'processors')
	if group_processors:
		group_processors.add_argument('--face-swapper-model', help = wording.get('help.face_swapper_model'), default = config.get_str_value('processors', 'face_swapper_model', 'inswapper_128_fp16'), choices = processors_choices.face_swapper_models)
		known_args, _ = program.parse_known_args()
		face_swapper_pixel_boost_choices = processors_choices.face_swapper_set.get(known_args.face_swapper_model)
		group_processors.add_argument('--face-swapper-pixel-boost', help = wording.get('help.face_swapper_pixel_boost'), default = config.get_str_value('processors', 'face_swapper_pixel_boost', get_first(face_swapper_pixel_boost_choices)), choices = face_swapper_pixel_boost_choices)
		facefusion.jobs.job_store.register_step_keys([ 'face_swapper_model', 'face_swapper_pixel_boost' ])


def apply_args(args : Args, apply_state_item : ApplyStateItem) -> None:
	apply_state_item('face_swapper_model', args.get('face_swapper_model'))
	apply_state_item('face_swapper_pixel_boost', args.get('face_swapper_pixel_boost'))


def pre_check() -> bool:
	model_hash_set = get_model_options().get('hashes')
	model_source_set = get_model_options().get('sources')

	return conditional_download_hashes(model_hash_set) and conditional_download_sources(model_source_set)


def pre_process(mode : ProcessMode) -> bool:
	# 如果使用 face_mappings，跳过源文件检查
	face_mappings = state_manager.get_item('face_mappings')
	if face_mappings and len(face_mappings) > 0:
		# 验证映射中的文件（支持URL）
		for mapping in face_mappings:
			source_path = mapping.get('source_path')
			reference_path = mapping.get('reference_path')

			# 检查源文件（支持URL）
			if not source_path:
				logger.error(f"Missing source image path", __name__)
				return False
			if not (source_path.startswith('http://') or source_path.startswith('https://')) and not has_image([source_path]):
				logger.error(f"Invalid source image: {source_path}", __name__)
				return False

			# 检查参考文件（支持URL）
			if not reference_path:
				logger.error(f"Missing reference image path", __name__)
				return False
			if not (reference_path.startswith('http://') or reference_path.startswith('https://')) and not has_image([reference_path]):
				logger.error(f"Invalid reference image: {reference_path}", __name__)
				return False
	else:
		# 原有的单源文件检查
		if not has_image(state_manager.get_item('source_paths')):
			logger.error(wording.get('choose_image_source') + wording.get('exclamation_mark'), __name__)
			return False
		source_image_paths = filter_image_paths(state_manager.get_item('source_paths'))
		source_frames = read_static_images(source_image_paths)
		source_faces = get_many_faces(source_frames)
		if not get_one_face(source_faces):
			logger.error(wording.get('no_source_face_detected') + wording.get('exclamation_mark'), __name__)
			return False
	if mode in [ 'output', 'preview' ] and not is_image(state_manager.get_item('target_path')) and not is_video(state_manager.get_item('target_path')):
		logger.error(wording.get('choose_image_or_video_target') + wording.get('exclamation_mark'), __name__)
		return False
	if mode == 'output' and not in_directory(state_manager.get_item('output_path')):
		logger.error(wording.get('specify_image_or_video_output') + wording.get('exclamation_mark'), __name__)
		return False
	if mode == 'output' and not same_file_extension(state_manager.get_item('target_path'), state_manager.get_item('output_path')):
		logger.error(wording.get('match_target_and_output_extension') + wording.get('exclamation_mark'), __name__)
		return False
	return True


def post_process() -> None:
	read_static_image.cache_clear()
	video_manager.clear_video_pool()
	if state_manager.get_item('video_memory_strategy') in [ 'strict', 'moderate' ]:
		get_static_model_initializer.cache_clear()
		clear_inference_pool()
	if state_manager.get_item('video_memory_strategy') == 'strict':
		content_analyser.clear_inference_pool()
		face_classifier.clear_inference_pool()
		face_detector.clear_inference_pool()
		face_landmarker.clear_inference_pool()
		face_masker.clear_inference_pool()
		face_recognizer.clear_inference_pool()


def swap_face(source_face : Face, target_face : Face, temp_vision_frame : VisionFrame) -> VisionFrame:
	# Validate inputs
	if not source_face:
		logger.error("swap_face called with None source_face", __name__)
		return temp_vision_frame
	if not target_face:
		logger.error("swap_face called with None target_face", __name__)
		return temp_vision_frame

	model_template = get_model_options().get('template')
	model_size = get_model_options().get('size')
	pixel_boost_size = unpack_resolution(state_manager.get_item('face_swapper_pixel_boost'))
	pixel_boost_total = pixel_boost_size[0] // model_size[0]
	crop_vision_frame, affine_matrix = warp_face_by_face_landmark_5(temp_vision_frame, target_face.landmark_set.get('5/68'), model_template, pixel_boost_size)
	temp_vision_frames = []
	crop_masks = []

	if 'box' in state_manager.get_item('face_mask_types'):
		box_mask = create_box_mask(crop_vision_frame, state_manager.get_item('face_mask_blur'), state_manager.get_item('face_mask_padding'))
		crop_masks.append(box_mask)

	if 'occlusion' in state_manager.get_item('face_mask_types'):
		occlusion_mask = create_occlusion_mask(crop_vision_frame)
		crop_masks.append(occlusion_mask)

	pixel_boost_vision_frames = implode_pixel_boost(crop_vision_frame, pixel_boost_total, model_size)
	for pixel_boost_vision_frame in pixel_boost_vision_frames:
		pixel_boost_vision_frame = prepare_crop_frame(pixel_boost_vision_frame)
		pixel_boost_vision_frame = forward_swap_face(source_face, pixel_boost_vision_frame)
		pixel_boost_vision_frame = normalize_crop_frame(pixel_boost_vision_frame)
		temp_vision_frames.append(pixel_boost_vision_frame)
	crop_vision_frame = explode_pixel_boost(temp_vision_frames, pixel_boost_total, model_size, pixel_boost_size)

	if 'area' in state_manager.get_item('face_mask_types'):
		face_landmark_68 = cv2.transform(target_face.landmark_set.get('68').reshape(1, -1, 2), affine_matrix).reshape(-1, 2)
		area_mask = create_area_mask(crop_vision_frame, face_landmark_68, state_manager.get_item('face_mask_areas'))
		crop_masks.append(area_mask)

	if 'region' in state_manager.get_item('face_mask_types'):
		region_mask = create_region_mask(crop_vision_frame, state_manager.get_item('face_mask_regions'))
		crop_masks.append(region_mask)

	crop_mask = numpy.minimum.reduce(crop_masks).clip(0, 1)
	temp_vision_frame = paste_back(temp_vision_frame, crop_vision_frame, crop_mask, affine_matrix)
	return temp_vision_frame


def forward_swap_face(source_face : Face, crop_vision_frame : VisionFrame) -> VisionFrame:
	face_swapper = get_inference_pool().get('face_swapper')
	model_type = get_model_options().get('type')
	face_swapper_inputs = {}

	if has_execution_provider('coreml') and model_type in [ 'ghost', 'uniface' ]:
		face_swapper.set_providers([ facefusion.choices.execution_provider_set.get('cpu') ])

	for face_swapper_input in face_swapper.get_inputs():
		if face_swapper_input.name == 'source':
			if model_type in [ 'blendswap', 'uniface' ]:
				face_swapper_inputs[face_swapper_input.name] = prepare_source_frame(source_face)
			else:
				face_swapper_inputs[face_swapper_input.name] = prepare_source_embedding(source_face)
		if face_swapper_input.name == 'target':
			face_swapper_inputs[face_swapper_input.name] = crop_vision_frame

	with conditional_thread_semaphore():
		crop_vision_frame = face_swapper.run(None, face_swapper_inputs)[0][0]

	return crop_vision_frame


def forward_convert_embedding(embedding : Embedding) -> Embedding:
	embedding_converter = get_inference_pool().get('embedding_converter')

	with conditional_thread_semaphore():
		embedding = embedding_converter.run(None,
		{
			'input': embedding
		})[0]

	return embedding


def prepare_source_frame(source_face : Face) -> VisionFrame:
	model_type = get_model_options().get('type')
	source_vision_frame = read_static_image(get_first(state_manager.get_item('source_paths')))

	if model_type == 'blendswap':
		source_vision_frame, _ = warp_face_by_face_landmark_5(source_vision_frame, source_face.landmark_set.get('5/68'), 'arcface_112_v2', (112, 112))
	if model_type == 'uniface':
		source_vision_frame, _ = warp_face_by_face_landmark_5(source_vision_frame, source_face.landmark_set.get('5/68'), 'ffhq_512', (256, 256))
	source_vision_frame = source_vision_frame[:, :, ::-1] / 255.0
	source_vision_frame = source_vision_frame.transpose(2, 0, 1)
	source_vision_frame = numpy.expand_dims(source_vision_frame, axis = 0).astype(numpy.float32)
	return source_vision_frame


def prepare_source_embedding(source_face : Face) -> Embedding:
	if not source_face:
		logger.error("prepare_source_embedding called with None source_face", __name__)
		return numpy.zeros((1, 512), dtype=numpy.float32)  # Return empty embedding

	model_type = get_model_options().get('type')

	if model_type == 'ghost':
		source_embedding, _ = convert_embedding(source_face)
		source_embedding = source_embedding.reshape(1, -1)
		return source_embedding

	if model_type == 'hyperswap':
		if not hasattr(source_face, 'normed_embedding') or source_face.normed_embedding is None:
			logger.error(f"source_face missing normed_embedding for hyperswap model", __name__)
			return numpy.zeros((1, 512), dtype=numpy.float32)
		source_embedding = source_face.normed_embedding.reshape((1, -1))
		return source_embedding

	if model_type == 'inswapper':
		if not hasattr(source_face, 'embedding') or source_face.embedding is None:
			logger.error(f"source_face missing embedding for inswapper model", __name__)
			return numpy.zeros((1, 512), dtype=numpy.float32)
		model_path = get_model_options().get('sources').get('face_swapper').get('path')
		model_initializer = get_static_model_initializer(model_path)
		source_embedding = source_face.embedding.reshape((1, -1))
		source_embedding = numpy.dot(source_embedding, model_initializer) / numpy.linalg.norm(source_embedding)
		return source_embedding

	_, source_normed_embedding = convert_embedding(source_face)
	source_embedding = source_normed_embedding.reshape(1, -1)
	return source_embedding


def convert_embedding(source_face : Face) -> Tuple[Embedding, Embedding]:
	embedding = source_face.embedding.reshape(-1, 512)
	embedding = forward_convert_embedding(embedding)
	embedding = embedding.ravel()
	normed_embedding = embedding / numpy.linalg.norm(embedding)
	return embedding, normed_embedding


def prepare_crop_frame(crop_vision_frame : VisionFrame) -> VisionFrame:
	model_mean = get_model_options().get('mean')
	model_standard_deviation = get_model_options().get('standard_deviation')

	crop_vision_frame = crop_vision_frame[:, :, ::-1] / 255.0
	crop_vision_frame = (crop_vision_frame - model_mean) / model_standard_deviation
	crop_vision_frame = crop_vision_frame.transpose(2, 0, 1)
	crop_vision_frame = numpy.expand_dims(crop_vision_frame, axis = 0).astype(numpy.float32)
	return crop_vision_frame


def normalize_crop_frame(crop_vision_frame : VisionFrame) -> VisionFrame:
	model_type = get_model_options().get('type')
	model_mean = get_model_options().get('mean')
	model_standard_deviation = get_model_options().get('standard_deviation')

	crop_vision_frame = crop_vision_frame.transpose(1, 2, 0)
	if model_type in [ 'ghost', 'hififace', 'hyperswap', 'uniface' ]:
		crop_vision_frame = crop_vision_frame * model_standard_deviation + model_mean
	crop_vision_frame = crop_vision_frame.clip(0, 1)
	crop_vision_frame = crop_vision_frame[:, :, ::-1] * 255
	return crop_vision_frame


def get_reference_frame(source_face : Face, target_face : Face, temp_vision_frame : VisionFrame) -> VisionFrame:
	return swap_face(source_face, target_face, temp_vision_frame)


def process_frame(inputs : FaceSwapperInputs) -> VisionFrame:
	import os
	frame_number = os.environ.get('FRAME_NUMBER', '?')
	reference_faces = inputs.get('reference_faces')
	source_face = inputs.get('source_face')
	target_vision_frame = inputs.get('target_vision_frame')
	many_faces = sort_and_filter_faces(get_many_faces([ target_vision_frame ]))
	# 只在有人脸时打印日志
	if len(many_faces) > 0:
		logger.info(f"[帧 {frame_number}] 检测到 {len(many_faces)} 个人脸", __name__)

	if state_manager.get_item('face_selector_mode') == 'many':
		if many_faces:
			for target_face in many_faces:
				target_vision_frame = swap_face(source_face, target_face, target_vision_frame)
	if state_manager.get_item('face_selector_mode') == 'one':
		target_face = get_one_face(many_faces)
		if target_face:
			target_vision_frame = swap_face(source_face, target_face, target_vision_frame)
	if state_manager.get_item('face_selector_mode') == 'reference':
		# ============================================================================
		# Enhanced Reference Mode (增强的 Reference 模式 - 支持多参考脸)
		# ============================================================================
		# 检查是否有多个参考脸映射
		face_mappings = inputs.get('face_mappings')

		if face_mappings and len(face_mappings) > 0:
			# 多参考脸模式：每个映射独立处理
			# 不需要每帧都打印这个

			# 记录已处理的目标脸，避免重复替换
			processed_indices = set()
			total_swapped = 0

			for mapping in face_mappings:
				source_face = mapping.get('source_face')
				reference_face = mapping.get('reference_face')
				threshold = mapping.get('similarity_threshold', state_manager.get_item('reference_face_distance'))

				# 使用预加载的源脸，或在此处加载（为了处理单张图片的情况）
				if not source_face and mapping.get('source_path'):
					source_path = mapping['source_path']
					# 如果是URL，先下载
					if source_path.startswith(('http://', 'https://')):
						import urllib.request
						import tempfile
						try:
							logger.debug(f"Downloading source image from {source_path}", __name__)
							with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
								urllib.request.urlretrieve(source_path, tmp_file.name)
								logger.debug(f"Downloaded to {tmp_file.name}", __name__)
								source_frame = read_static_image(tmp_file.name)
								if source_frame is not None:
									logger.debug(f"Successfully read source image, shape: {source_frame.shape}", __name__)
								else:
									logger.error(f"Failed to read source image from {tmp_file.name}", __name__)
								os.unlink(tmp_file.name)  # 清理临时文件
						except Exception as e:
							logger.error(f"Failed to download source image from {source_path}: {e}", __name__)
							source_frame = None
					else:
						source_frame = read_static_image(source_path)

					if source_frame is not None:
						temp_faces = get_many_faces([source_frame])
						if temp_faces:
							source_face = get_first(temp_faces)
							logger.debug(f"Found source face with embedding shape: {source_face.embedding.shape if source_face and hasattr(source_face, 'embedding') else 'None'}", __name__)
						else:
							logger.warn(f"No faces detected in source image {source_path}", __name__)

				# 使用预加载的参考脸，或在此处加载（为了处理单张图片的情况）
				if not reference_face and mapping.get('reference_path'):
					reference_path = mapping['reference_path']
					# 如果是URL，先下载
					if reference_path.startswith(('http://', 'https://')):
						import urllib.request
						import tempfile
						try:
							logger.debug(f"Downloading reference image from {reference_path}", __name__)
							with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
								urllib.request.urlretrieve(reference_path, tmp_file.name)
								logger.debug(f"Downloaded to {tmp_file.name}", __name__)
								ref_frame = read_static_image(tmp_file.name)
								if ref_frame is not None:
									logger.debug(f"Successfully read reference image, shape: {ref_frame.shape}", __name__)
								else:
									logger.error(f"Failed to read reference image from {tmp_file.name}", __name__)
								os.unlink(tmp_file.name)  # 清理临时文件
						except Exception as e:
							logger.error(f"Failed to download reference image from {reference_path}: {e}", __name__)
							ref_frame = None
					else:
						ref_frame = read_static_image(reference_path)

					if ref_frame is not None:
						temp_faces = get_many_faces([ref_frame])
						if temp_faces:
							reference_face = get_first(temp_faces)
							logger.debug(f"Found reference face with embedding shape: {reference_face.embedding.shape if reference_face and hasattr(reference_face, 'embedding') else 'None'}", __name__)
						else:
							logger.warn(f"No faces detected in reference image {reference_path}", __name__)

				# 查找相似的脸并替换
				if source_face and reference_face:
					matched_count = 0
					for idx, target_face in enumerate(many_faces):
						if idx not in processed_indices:
							# 使用 FaceFusion 内置的相似度比较
							similarity = 1 - numpy.dot(target_face.normed_embedding, reference_face.normed_embedding)
							is_similar = similarity < threshold
							# 只在匹配成功时打印详细信息

							if is_similar:
								target_vision_frame = swap_face(source_face, target_face, target_vision_frame)
								processed_indices.add(idx)
								matched_count += 1
								source_name = mapping.get("source_path", "").split('/')[-1]
								logger.info(f"  ✓ 人脸{idx} 替换为 {source_name} (相似度: {similarity:.3f})", __name__)
								# 继续查找，因为可能有多个相似的脸
					total_swapped += matched_count
					# 不需要打印没有匹配的情况
				else:
					if not source_face:
						logger.warn(f"Failed to load source face from {mapping.get('source_path')}", __name__)
					if not reference_face:
						logger.warn(f"Failed to load reference face from {mapping.get('reference_path')}", __name__)

			if total_swapped > 0:
				logger.info(f"[帧 {frame_number}] 完成: 替换了 {total_swapped}/{len(many_faces)} 个人脸", __name__)
		else:
			# 原始单参考脸模式（保持兼容）
			similar_faces = find_similar_faces(many_faces, reference_faces, state_manager.get_item('reference_face_distance'))
			if similar_faces:
				for similar_face in similar_faces:
					target_vision_frame = swap_face(source_face, similar_face, target_vision_frame)
	return target_vision_frame


# ============================================================================
# Helper Functions for Multi-Reference Support
# ============================================================================


# compare_faces 函数已从 face_selector 模块导入，无需重复定义

def process_frames(source_paths : List[str], queue_payloads : List[QueuePayload], update_progress : UpdateProgress) -> None:
	import copy
	reference_faces = get_reference_faces() if 'reference' in state_manager.get_item('face_selector_mode') else None

	# 获取face_mappings配置
	face_mappings_original = state_manager.get_item('face_mappings')
	face_mappings = None

	if face_mappings_original and len(face_mappings_original) > 0:
		# 创建深拷贝以存储预加载的人脸
		face_mappings = copy.deepcopy(face_mappings_original)
		# 多映射模式：预加载所有源脸和参考脸
		for mapping in face_mappings:
			# 加载源脸
			if not mapping.get('source_face') and mapping.get('source_path'):
				source_path = mapping['source_path']
				if source_path.startswith(('http://', 'https://')):
					import urllib.request
					import tempfile
					try:
						with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
							urllib.request.urlretrieve(source_path, tmp_file.name)
							source_frame = read_static_image(tmp_file.name)
							os.unlink(tmp_file.name)
					except Exception as e:
						logger.error(f"Failed to download source image from {source_path}: {e}", __name__)
						source_frame = None
				else:
					source_frame = read_static_image(source_path)

				if source_frame is not None:
					temp_faces = get_many_faces([source_frame])
					if temp_faces:
						mapping['source_face'] = get_first(temp_faces)
						logger.info(f"Successfully preloaded source face from {source_path}", __name__)
					else:
						logger.warn(f"No faces detected during preload from {source_path}", __name__)

			# 加载参考脸
			if not mapping.get('reference_face') and mapping.get('reference_path'):
				reference_path = mapping['reference_path']
				if reference_path.startswith(('http://', 'https://')):
					import urllib.request
					import tempfile
					try:
						with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
							urllib.request.urlretrieve(reference_path, tmp_file.name)
							ref_frame = read_static_image(tmp_file.name)
							os.unlink(tmp_file.name)
					except Exception as e:
						logger.error(f"Failed to download reference image from {reference_path}: {e}", __name__)
						ref_frame = None
				else:
					ref_frame = read_static_image(reference_path)

				if ref_frame is not None:
					temp_faces = get_many_faces([ref_frame])
					if temp_faces:
						mapping['reference_face'] = get_first(temp_faces)
						logger.info(f"Successfully preloaded reference face from {reference_path}", __name__)
					else:
						logger.warn(f"No faces detected during preload from {reference_path}", __name__)

		source_face = None  # 多映射模式不需要单一source_face
	else:
		# 原始单源脸模式
		source_frames = read_static_images(source_paths)
		source_faces = []

		for source_frame in source_frames:
			temp_faces = get_many_faces([ source_frame ])
			temp_faces = sort_faces_by_order(temp_faces, 'large-small')
			if temp_faces:
				source_faces.append(get_first(temp_faces))
		source_face = get_average_face(source_faces)

	for queue_payload in process_manager.manage(queue_payloads):
		target_vision_path = queue_payload['frame_path']
		# 从文件名提取帧号
		frame_number = target_vision_path.split('/')[-1].split('.')[0]
		os.environ['FRAME_NUMBER'] = frame_number
		target_vision_frame = read_image(target_vision_path)
		output_vision_frame = process_frame(
		{
			'reference_faces': reference_faces,
			'source_face': source_face,
			'target_vision_frame': target_vision_frame,
			'face_mappings': face_mappings  # 传递face_mappings
		})
		if output_vision_frame is not None:
			write_image(target_vision_path, output_vision_frame)
		else:
			logger.error(f"帧 {frame_number} 处理失败，返回空图像", __name__)
		update_progress(1)


def process_image(source_paths : List[str], target_path : str, output_path : str) -> None:
	import copy
	reference_faces = get_reference_faces() if 'reference' in state_manager.get_item('face_selector_mode') else None

	# 获取face_mappings配置
	face_mappings_original = state_manager.get_item('face_mappings')
	face_mappings = None

	if face_mappings_original and len(face_mappings_original) > 0:
		# 创建深拷贝以存储预加载的人脸
		face_mappings = copy.deepcopy(face_mappings_original)
		# 多映射模式：预加载所有源脸和参考脸
		for mapping in face_mappings:
			# 加载源脸
			if not mapping.get('source_face') and mapping.get('source_path'):
				source_path = mapping['source_path']
				if source_path.startswith(('http://', 'https://')):
					import urllib.request
					import tempfile
					try:
						with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
							urllib.request.urlretrieve(source_path, tmp_file.name)
							source_frame = read_static_image(tmp_file.name)
							os.unlink(tmp_file.name)
					except Exception as e:
						logger.error(f"Failed to download source image from {source_path}: {e}", __name__)
						source_frame = None
				else:
					source_frame = read_static_image(source_path)

				if source_frame is not None:
					temp_faces = get_many_faces([source_frame])
					if temp_faces:
						mapping['source_face'] = get_first(temp_faces)
						logger.info(f"Successfully preloaded source face from {source_path}", __name__)
					else:
						logger.warn(f"No faces detected during preload from {source_path}", __name__)

			# 加载参考脸
			if not mapping.get('reference_face') and mapping.get('reference_path'):
				reference_path = mapping['reference_path']
				if reference_path.startswith(('http://', 'https://')):
					import urllib.request
					import tempfile
					try:
						with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
							urllib.request.urlretrieve(reference_path, tmp_file.name)
							ref_frame = read_static_image(tmp_file.name)
							os.unlink(tmp_file.name)
					except Exception as e:
						logger.error(f"Failed to download reference image from {reference_path}: {e}", __name__)
						ref_frame = None
				else:
					ref_frame = read_static_image(reference_path)

				if ref_frame is not None:
					temp_faces = get_many_faces([ref_frame])
					if temp_faces:
						mapping['reference_face'] = get_first(temp_faces)
						logger.info(f"Successfully preloaded reference face from {reference_path}", __name__)
					else:
						logger.warn(f"No faces detected during preload from {reference_path}", __name__)

		source_face = None  # 多映射模式不需要单一source_face
	else:
		# 原始单源脸模式
		source_frames = read_static_images(source_paths)
		source_faces = []

		for source_frame in source_frames:
			temp_faces = get_many_faces([ source_frame ])
			temp_faces = sort_faces_by_order(temp_faces, 'large-small')
			if temp_faces:
				source_faces.append(get_first(temp_faces))
		source_face = get_average_face(source_faces)

	target_vision_frame = read_static_image(target_path)
	output_vision_frame = process_frame(
	{
		'reference_faces': reference_faces,
		'source_face': source_face,
		'target_vision_frame': target_vision_frame,
		'face_mappings': face_mappings  # 传递face_mappings
	})
	write_image(output_path, output_vision_frame)


def process_video(source_paths : List[str], temp_frame_paths : List[str]) -> None:
	processors.multi_process_frames(source_paths, temp_frame_paths, process_frames)
