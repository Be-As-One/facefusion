#!/bin/bash
# RunPod Serverless 部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
DOCKER_IMAGE_NAME="facefusion-runpod"
DOCKER_TAG="latest"
DOCKER_REGISTRY="your-registry"  # 修改为你的 Docker 仓库
FULL_IMAGE_NAME="${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"

# 函数：打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_step "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        print_error "Git 未安装，请先安装 Git"
        exit 1
    fi
    
    print_message "依赖检查通过"
}

# 清理旧构建
cleanup() {
    print_step "清理旧构建..."
    
    # 删除悬空镜像
    docker image prune -f
    
    # 删除未使用的容器
    docker container prune -f
    
    print_message "清理完成"
}

# 构建 Docker 镜像
build_image() {
    print_step "构建 Docker 镜像..."
    
    # 确保在正确的目录
    if [ ! -f "Dockerfile.runpod" ]; then
        print_error "Dockerfile.runpod 文件不存在，请确保在正确的目录中运行此脚本"
        exit 1
    fi
    
    # 构建镜像
    docker build -f Dockerfile.runpod -t ${DOCKER_IMAGE_NAME}:${DOCKER_TAG} .
    
    # 标记镜像
    docker tag ${DOCKER_IMAGE_NAME}:${DOCKER_TAG} ${FULL_IMAGE_NAME}
    
    print_message "镜像构建完成: ${FULL_IMAGE_NAME}"
}

# 测试镜像
test_image() {
    print_step "测试镜像..."
    
    # 创建测试容器
    CONTAINER_ID=$(docker run -d --rm \
        -e MAX_CONCURRENCY=1 \
        -e DEBUG_MODE=true \
        ${DOCKER_IMAGE_NAME}:${DOCKER_TAG})
    
    # 等待容器启动
    sleep 10
    
    # 检查容器状态
    if docker ps | grep -q ${CONTAINER_ID}; then
        print_message "容器启动成功"
        
        # 停止测试容器
        docker stop ${CONTAINER_ID}
        print_message "测试通过"
    else
        print_error "容器启动失败"
        docker logs ${CONTAINER_ID}
        exit 1
    fi
}

# 推送镜像
push_image() {
    print_step "推送镜像到仓库..."
    
    # 登录 Docker 仓库 (如果需要)
    # docker login
    
    # 推送镜像
    docker push ${FULL_IMAGE_NAME}
    
    print_message "镜像推送完成: ${FULL_IMAGE_NAME}"
}

# 生成 RunPod 配置
generate_runpod_config() {
    print_step "生成 RunPod 配置..."
    
    cat > runpod_config.json << EOF
{
    "name": "FaceFusion Serverless",
    "image": "${FULL_IMAGE_NAME}",
    "gpu": {
        "type": "RTX A6000",
        "count": 1
    },
    "container": {
        "cpu": 4,
        "memory": 16384,
        "disk": 50
    },
    "scaling": {
        "min_workers": 0,
        "max_workers": 5,
        "idle_timeout": 60
    },
    "environment": {
        "MAX_CONCURRENCY": "3",
        "LOG_LEVEL": "INFO",
        "CUDA_VISIBLE_DEVICES": "0"
    },
    "network_volume": {
        "enabled": false
    }
}
EOF
    
    print_message "RunPod 配置已生成: runpod_config.json"
}

# 显示部署信息
show_deployment_info() {
    print_step "部署信息"
    
    echo "========================================"
    echo "FaceFusion RunPod Serverless 部署信息"
    echo "========================================"
    echo "Docker 镜像: ${FULL_IMAGE_NAME}"
    echo "Handler 路径: /app/runpod_handler.py"
    echo "最大并发数: ${MAX_CONCURRENCY:-3}"
    echo "环境配置: .env.runpod"
    echo "========================================"
    echo ""
    echo "下一步操作："
    echo "1. 在 RunPod 控制台创建新的 Serverless 端点"
    echo "2. 使用镜像: ${FULL_IMAGE_NAME}"
    echo "3. 配置 GPU 和内存设置"
    echo "4. 设置环境变量"
    echo "5. 部署并测试端点"
    echo ""
    echo "测试 API 调用示例："
    echo "curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -H 'Authorization: Bearer YOUR_API_KEY' \\"
    echo "  -d '{"
    echo "    \"input\": {"
    echo "      \"source_url\": \"https://example.com/source.jpg\","
    echo "      \"target_url\": \"https://example.com/target.jpg\","
    echo "      \"resolution\": \"1024x1024\","
    echo "      \"media_type\": \"image\""
    echo "    }"
    echo "  }'"
}

# 主函数
main() {
    print_message "开始 FaceFusion RunPod Serverless 部署"
    
    # 解析命令行参数
    BUILD_ONLY=false
    SKIP_TEST=false
    SKIP_PUSH=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            --skip-test)
                SKIP_TEST=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --registry)
                DOCKER_REGISTRY="$2"
                FULL_IMAGE_NAME="${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"
                shift 2
                ;;
            --tag)
                DOCKER_TAG="$2"
                FULL_IMAGE_NAME="${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"
                shift 2
                ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo "选项:"
                echo "  --build-only     仅构建镜像，不推送"
                echo "  --skip-test      跳过镜像测试"
                echo "  --skip-push      跳过镜像推送"
                echo "  --registry REG   指定 Docker 仓库"
                echo "  --tag TAG        指定镜像标签"
                echo "  -h, --help       显示帮助信息"
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    # 执行部署步骤
    check_dependencies
    cleanup
    build_image
    
    if [ "$SKIP_TEST" = false ]; then
        test_image
    fi
    
    if [ "$BUILD_ONLY" = false ] && [ "$SKIP_PUSH" = false ]; then
        push_image
    fi
    
    generate_runpod_config
    show_deployment_info
    
    print_message "部署脚本执行完成！"
}

# 运行主函数
main "$@"