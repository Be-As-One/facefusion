#!/usr/bin/env python3
"""
RunPod Handler 测试脚本
用于本地测试 RunPod Handler 的功能
"""

import asyncio
import json
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_sync_handler():
    """测试同步 Handler"""
    print("=" * 50)
    print("测试同步 Handler")
    print("=" * 50)

    try:
        from runpod_handler import health_check, handler

        # 测试健康检查
        print("\n1. 测试健康检查...")
        health_result = health_check()
        print(f"健康检查结果: {json.dumps(health_result, indent=2)}")

        # 测试基本的 Handler 调用
        print("\n2. 测试 Handler 调用...")
        test_job = {
            "id": "test-job-001",
            "input": {
                "source_url": "https://example.com/source.jpg",
                "target_url": "https://example.com/target.jpg",
                "resolution": "512x512"
            }
        }

        print(f"测试输入: {json.dumps(test_job, indent=2)}")

        start_time = time.time()
        result = handler(test_job)
        end_time = time.time()

        print(f"处理时间: {end_time - start_time:.2f} 秒")
        print(f"结果: {json.dumps(result, indent=2)}")

        return result

    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_async_handler():
    """测试异步 Handler"""
    print("=" * 50)
    print("测试异步 Handler")
    print("=" * 50)

    try:
        from runpod_handler import handler

        # 测试异步处理
        test_job = {
            "id": "async-test-job-001",
            "input": {
                "source_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
                "target_url": "https://test.deepswaper.net/_next/image?url=https%3A%2F%2Fcdn-test.deepswaper.net%2F%2Fface-swap%2F2.png&w=256&q=75",
                "resolution": "256x256"
            }
        }

        print(f"异步测试输入: {json.dumps(test_job, indent=2)}")

        start_time = time.time()
        result = handler(test_job)
        end_time = time.time()

        print(f"异步处理时间: {end_time - start_time:.2f} 秒")
        print(f"异步结果: {json.dumps(result, indent=2)}")

        return result

    except Exception as e:
        logger.error(f"异步测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_concurrent_requests():
    """测试并发请求处理"""
    print("=" * 50)
    print("测试并发请求处理")
    print("=" * 50)

    try:
        from runpod_handler import handler

        # 创建多个测试任务
        test_jobs = []
        for i in range(3):
            job = {
                "id": f"concurrent-test-job-{i:03d}",
                "input": {
                    "source_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
                    "target_url": "https://test.deepswaper.net/_next/image?url=https%3A%2F%2Fcdn-test.deepswaper.net%2F%2Fface-swap%2F2.png&w=256&q=75",
                    "resolution": "256x256"
                }
            }
            test_jobs.append(job)

        print(f"并发测试任务数量: {len(test_jobs)}")

        # 并发执行（实际是顺序执行，因为 handler 不是异步的）
        start_time = time.time()
        results = []
        for job in test_jobs:
            try:
                result = handler(job)
                results.append(result)
            except Exception as e:
                results.append(e)
        end_time = time.time()

        print(f"并发处理总时间: {end_time - start_time:.2f} 秒")
        print(f"平均每个任务时间: {(end_time - start_time) / len(test_jobs):.2f} 秒")

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"任务 {i} 失败: {str(result)}")
            else:
                print(f"任务 {i} 状态: {result.get('status', 'unknown')}")

        return results

    except Exception as e:
        logger.error(f"并发测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_input_validation():
    """测试输入验证"""
    print("=" * 50)
    print("测试输入验证")
    print("=" * 50)

    try:
        from runpod_handler import handler

        # 测试无效输入
        invalid_jobs = [
            {
                "id": "invalid-1",
                "input": {}  # 缺少必需参数
            },
            {
                "id": "invalid-2",
                "input": {
                    "source_url": "invalid-url",  # 无效 URL
                    "target_url": "also-invalid"
                }
            },
            {
                "id": "invalid-3",
                "input": {
                    "source_url": "https://example.com/source.jpg"
                    # 缺少 target_url
                }
            }
        ]

        for i, job in enumerate(invalid_jobs):
            print(f"\n测试无效输入 {i+1}:")
            print(f"输入: {json.dumps(job, indent=2)}")

            result = handler(job)
            print(f"结果: {result.get('status', 'unknown')}")

            if result.get('status') in ['失败', 'error']:
                print(f"错误信息: {result.get('error', 'unknown error')}")

        return True

    except Exception as e:
        logger.error(f"输入验证测试失败: {str(e)}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始 RunPod Handler 测试")
    print("=" * 60)

    results = {}

    # 1. 测试同步处理
    print("\n")
    sync_result = test_sync_handler()
    results['sync_handler'] = sync_result is not None

    # 2. 测试异步处理
    print("\n")
    async_result = test_async_handler()
    results['async_handler'] = async_result is not None

    # 3. 测试并发处理
    print("\n")
    concurrent_result = test_concurrent_requests()
    results['concurrent_handler'] = concurrent_result is not None

    # 4. 测试输入验证
    print("\n")
    validation_result = test_input_validation()
    results['input_validation'] = validation_result

    # 输出测试总结
    print("\n" + "=" * 60)
    print("🧪 测试总结")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")

    overall_success = all(results.values())
    print(f"\n总体结果: {'✅ 所有测试通过' if overall_success else '❌ 部分测试失败'}")

    return overall_success


if __name__ == "__main__":
    # 设置环境变量用于测试
    import os
    os.environ['DEBUG_MODE'] = 'true'
    os.environ['MAX_CONCURRENCY'] = '2'

    success = run_all_tests()
    exit(0 if success else 1)
