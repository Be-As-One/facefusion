#!/usr/bin/env python3
"""
RunPod Serverless 端点测试脚本
用于测试已部署的 RunPod Serverless 端点
"""

import json
import time
import requests
import os

# 配置
RUNPOD_API_BASE = "https://api.runpod.ai/v2"
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
ENDPOINT_ID = os.getenv('RUNPOD_ENDPOINT_ID')

# 测试用的图片URL
TEST_IMAGES = {
    "source": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
    "target": "https://images.unsplash.com/photo-1494790108755-2616b612b5bc?w=512&h=512&fit=crop&crop=face"
}


def test_runpod_endpoint():
    """测试 RunPod Serverless 端点"""

    if not RUNPOD_API_KEY:
        print("❌ 请设置 RUNPOD_API_KEY 环境变量")
        return False

    if not ENDPOINT_ID:
        print("❌ 请设置 RUNPOD_ENDPOINT_ID 环境变量")
        return False

    print("🚀 开始测试 RunPod Serverless 端点")
    print(f"端点ID: {ENDPOINT_ID}")
    print("=" * 60)

    # 测试1: 同步调用
    success = test_sync_request()

    # 测试2: 异步调用
    if success:
        success = test_async_request()

    # 测试3: 批量调用
    if success:
        success = test_batch_requests()

    return success


def test_sync_request():
    """测试同步请求"""
    print("\n📞 测试1: 同步调用")
    print("-" * 40)

    url = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": {
            "source_url": TEST_IMAGES["source"],
            "target_url": TEST_IMAGES["target"],
            "resolution": "512x512",
            "media_type": "image"
        }
    }

    print(f"请求URL: {url}")
    print(f"请求载荷: {json.dumps(payload, indent=2)}")

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers,
                                 json=payload, timeout=300)
        end_time = time.time()

        print(f"响应状态: {response.status_code}")
        print(f"处理时间: {end_time - start_time:.2f} 秒")

        if response.status_code == 200:
            result = response.json()
            print(f"响应结果: {json.dumps(result, indent=2)}")

            if result.get('status') == 'success':
                print("✅ 同步调用测试成功")
                return True
            else:
                print(f"❌ 处理失败: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ API 调用失败: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False


def test_async_request():
    """测试异步请求"""
    print("\n⏰ 测试2: 异步调用")
    print("-" * 40)

    # 启动异步任务
    run_url = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/run"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "input": {
            "source_url": TEST_IMAGES["source"],
            "target_url": TEST_IMAGES["target"],
            "resolution": "1024x1024",
            "media_type": "image"
        }
    }

    try:
        # 提交任务
        response = requests.post(
            run_url, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            print(f"❌ 任务提交失败: {response.text}")
            return False

        run_result = response.json()
        job_id = run_result.get('id')

        if not job_id:
            print(f"❌ 未获取到任务ID: {run_result}")
            return False

        print(f"✅ 任务已提交，ID: {job_id}")

        # 轮询任务状态
        status_url = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/status/{job_id}"

        max_wait_time = 300  # 最多等待5分钟
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            status_response = requests.get(
                status_url, headers=headers, timeout=30)

            if status_response.status_code == 200:
                status_result = status_response.json()
                status = status_result.get('status')

                print(f"任务状态: {status}")

                if status == 'COMPLETED':
                    output = status_result.get('output', {})
                    print(f"✅ 异步任务完成: {json.dumps(output, indent=2)}")
                    return True
                elif status == 'FAILED':
                    error = status_result.get('error', 'Unknown error')
                    print(f"❌ 任务失败: {error}")
                    return False
                elif status in ['IN_QUEUE', 'IN_PROGRESS']:
                    time.sleep(10)  # 等待10秒后重试
                    continue
                else:
                    print(f"❓ 未知状态: {status}")
                    time.sleep(5)
            else:
                print(f"❌ 状态查询失败: {status_response.text}")
                return False

        print("❌ 任务超时")
        return False

    except Exception as e:
        print(f"❌ 异步测试异常: {str(e)}")
        return False


def test_batch_requests():
    """测试批量请求"""
    print("\n📦 测试3: 批量调用")
    print("-" * 40)

    url = f"{RUNPOD_API_BASE}/{ENDPOINT_ID}/runsync"
    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    # 创建3个不同的测试任务
    test_cases = [
        {
            "source_url": TEST_IMAGES["source"],
            "target_url": TEST_IMAGES["target"],
            "resolution": "256x256",
            "media_type": "image"
        },
        {
            "source_url": TEST_IMAGES["source"],
            "target_url": TEST_IMAGES["target"],
            "resolution": "512x512",
            "media_type": "image"
        },
        {
            "source_url": TEST_IMAGES["source"],
            "target_url": TEST_IMAGES["target"],
            "resolution": "768x768",
            "media_type": "image"
        }
    ]

    success_count = 0
    total_time = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n批量测试 {i}/3 - 分辨率: {test_case['resolution']}")

        payload = {"input": test_case}

        try:
            start_time = time.time()
            response = requests.post(
                url, headers=headers, json=payload, timeout=300)
            end_time = time.time()

            request_time = end_time - start_time
            total_time += request_time

            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"✅ 测试 {i} 成功 ({request_time:.2f}s)")
                    success_count += 1
                else:
                    print(f"❌ 测试 {i} 处理失败: {result.get('error', 'Unknown')}")
            else:
                print(f"❌ 测试 {i} API 失败: {response.status_code}")

        except Exception as e:
            print(f"❌ 测试 {i} 异常: {str(e)}")

    print(f"\n📊 批量测试结果:")
    print(f"成功: {success_count}/{len(test_cases)}")
    print(f"总时间: {total_time:.2f}s")
    print(f"平均时间: {total_time / len(test_cases):.2f}s")

    return success_count == len(test_cases)


def main():
    """主函数"""
    print("🧪 RunPod Serverless 端点测试工具")
    print("=" * 60)

    # 显示配置信息
    print("\n📋 配置信息:")
    print(f"API Key: {'✅ 已配置' if RUNPOD_API_KEY else '❌ 未配置'}")
    print(f"端点ID: {'✅ 已配置' if ENDPOINT_ID else '❌ 未配置'}")

    if not RUNPOD_API_KEY or not ENDPOINT_ID:
        print("\n❌ 请设置以下环境变量:")
        print("export RUNPOD_API_KEY='your-api-key'")
        print("export RUNPOD_ENDPOINT_ID='your-endpoint-id'")
        return False

    # 运行测试
    success = test_runpod_endpoint()

    print("\n" + "=" * 60)
    if success:
        print("🎉 所有测试通过！RunPod Serverless 端点工作正常")
    else:
        print("❌ 测试失败，请检查端点配置和实现")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
