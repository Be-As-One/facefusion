# FaceFusion RunPod Serverless 部署指南

本文档介绍如何将 FaceFusion 部署为 RunPod Serverless Worker，实现高效的云端人脸交换服务。

## 🚀 快速开始

### 1. 准备工作

确保您已经安装了以下工具：
- Docker
- Git
- RunPod 账户

### 2. 克隆项目

```bash
git clone <your-repo-url>
cd video-faceswap
```

### 3. 配置环境变量

复制环境配置文件：
```bash
cp .env.runpod .env
```

编辑 `.env` 文件，配置您的存储服务（选择一个或多个）：

```bash
# Google Cloud Storage
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_BUCKET="your-bucket"
GOOGLE_CLOUD_CREDENTIALS_PATH="/path/to/credentials.json"

# Cloudflare R2
CLOUDFLARE_R2_ACCESS_KEY_ID="your-access-key"
CLOUDFLARE_R2_SECRET_ACCESS_KEY="your-secret-key"
CLOUDFLARE_R2_BUCKET="your-bucket"
CLOUDFLARE_R2_ENDPOINT="your-endpoint"

# 或者 Cloudflare Images
CLOUDFLARE_IMAGES_API_TOKEN="your-api-token"
CLOUDFLARE_IMAGES_ACCOUNT_ID="your-account-id"
```

### 4. 构建和部署

使用自动化部署脚本：

```bash
# 完整部署（构建 + 测试 + 推送）
./deploy_runpod.sh --registry your-docker-registry

# 仅构建镜像
./deploy_runpod.sh --build-only

# 跳过测试
./deploy_runpod.sh --skip-test --registry your-docker-registry

# 查看帮助
./deploy_runpod.sh --help
```

### 5. 在 RunPod 控制台配置

1. 登录 [RunPod 控制台](https://www.runpod.io/)
2. 创建新的 Serverless 端点
3. 配置以下参数：
   - **镜像**: `your-registry/facefusion-runpod:latest`
   - **GPU**: RTX A6000 或更高
   - **内存**: 16GB+
   - **存储**: 50GB+
   - **最大并发数**: 3-5

4. 设置环境变量：
   ```
   MAX_CONCURRENCY=3
   LOG_LEVEL=INFO
   CUDA_VISIBLE_DEVICES=0
   ```

## 📡 API 使用

### 基本人脸交换

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "input": {
      "source_url": "https://example.com/source-face.jpg",
      "target_url": "https://example.com/target-image.jpg",
      "resolution": "1024x1024",
      "media_type": "image"
    }
  }'
```

### 视频人脸交换

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "input": {
      "source_url": "https://example.com/source-face.jpg",
      "target_url": "https://example.com/target-video.mp4",
      "resolution": "1920x1080",
      "media_type": "video"
    }
  }'
```

### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| `source_url` | string | 是 | - | 源人脸图像的URL |
| `target_url` | string | 是 | - | 目标图像/视频的URL |
| `resolution` | string | 否 | "1024x1024" | 输出分辨率 |
| `media_type` | string | 否 | "image" | 媒体类型 ("image" 或 "video") |

### 响应格式

成功响应：
```json
{
  "status": "success",
  "result": {
    "original_url": "https://storage.com/result.jpg",
    "gif_url": "https://storage.com/result.gif",
    "webp_url": "https://storage.com/result.webp"
  },
  "processing_time": 15.6
}
```

错误响应：
```json
{
  "status": "error",
  "error": "Error description",
  "traceback": "Detailed error trace"
}
```

## 🛠️ 高级配置

### 并发控制

系统支持动态并发调整：

```bash
# 环境变量
MAX_CONCURRENCY=5          # 最大并发数
MIN_CONCURRENCY=1          # 最小并发数
CONCURRENCY_ADJUSTMENT_THRESHOLD=0.5  # 调整阈值
```

### 性能优化

```bash
# GPU 配置
CUDA_VISIBLE_DEVICES=0
CUDA_MEMORY_FRACTION=0.9

# CPU 配置
OPENCV_THREAD_COUNT=4
NUMPY_THREADS=4
OMP_NUM_THREADS=4

# 内存管理
MAX_MEMORY_USAGE=8GB
MEMORY_CLEANUP_INTERVAL=300
```

### 存储配置

系统支持多种存储后端：

1. **Google Cloud Storage** - 推荐用于生产环境
2. **Cloudflare R2** - 成本效益高
3. **Cloudflare Images** - 自动优化和CDN
4. **AWS S3** - 广泛兼容

### 监控和日志

```bash
# 日志级别
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# 健康检查
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10

# 调试模式
DEBUG_MODE=false
SAVE_INTERMEDIATE_RESULTS=false
VERBOSE_LOGGING=false
```

## 🔧 故障排除

### 常见问题

1. **镜像构建失败**
   - 检查 Docker 是否正确安装
   - 确保有足够的磁盘空间
   - 检查网络连接

2. **容器启动失败**
   - 检查环境变量配置
   - 查看容器日志：`docker logs <container_id>`
   - 确认 GPU 驱动正确安装

3. **API 请求失败**
   - 验证 RunPod API Key
   - 检查端点配置
   - 确认输入 URL 可访问

4. **处理超时**
   - 增加 `REQUEST_TIMEOUT` 值
   - 检查网络连接
   - 优化输入文件大小

### 日志查看

```bash
# 查看 RunPod 日志
# 在 RunPod 控制台 -> 端点 -> 日志

# 本地测试日志
docker logs <container_id>

# 启用详细日志
export VERBOSE_LOGGING=true
```

## 📈 性能基准

### 典型性能指标

| 任务类型 | 分辨率 | 处理时间 | GPU 使用率 |
|----------|--------|----------|------------|
| 图像人脸交换 | 1024x1024 | 5-10秒 | 80-90% |
| 视频人脸交换 | 1080p (10秒) | 60-120秒 | 85-95% |
| 视频人脸交换 | 4K (10秒) | 180-300秒 | 90-100% |

### 优化建议

1. **预热模型** - 首次请求会较慢，后续请求会更快
2. **批处理** - 对于大量任务，考虑批处理
3. **分辨率平衡** - 在质量和速度之间找到平衡
4. **并发控制** - 根据GPU内存调整并发数

## 🔒 安全考虑

1. **API Key 安全** - 不要在客户端代码中暴露 API Key
2. **输入验证** - 系统会验证输入 URL 的有效性
3. **存储加密** - 确保存储服务启用加密
4. **访问控制** - 配置适当的存储访问权限

## 📞 支持

如果您遇到问题或需要帮助：

1. 查看本文档的故障排除部分
2. 检查 RunPod 社区论坛
3. 提交 GitHub Issue

## 📄 许可证

本项目遵循相应的开源许可证。详情请查看 LICENSE 文件。