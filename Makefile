# Netcup流量限制测试器 Makefile

.PHONY: help build run stop clean logs shell test logs-info

# 检测Docker Compose命令
DOCKER_COMPOSE_CMD := $(shell \
	if docker compose version >/dev/null 2>&1; then \
		echo "docker compose"; \
	elif command -v docker-compose >/dev/null 2>&1; then \
		echo "docker-compose"; \
	else \
		echo ""; \
	fi)

# 默认目标
help:
	@echo "可用命令:"
	@echo "  build        - 构建Docker镜像"
	@echo "  run          - 启动服务"
	@echo "  stop         - 停止容器"
	@echo "  clean        - 停止并删除容器和镜像"
	@echo "  logs         - 查看容器日志"
	@echo "  logs-info    - 查看日志文件信息"
	@echo "  shell        - 进入容器shell"
	@echo "  test         - 测试API接口"
	@echo ""
	@echo "当前使用: $(DOCKER_COMPOSE_CMD)"

# 构建镜像
build:
	@echo "构建Docker镜像..."
	$(DOCKER_COMPOSE_CMD) build

# 启动服务
run:
	@echo "启动Netcup流量限制测试器服务..."
	$(DOCKER_COMPOSE_CMD) up -d
	@echo "服务已启动，查看日志请运行: make logs"

# 停止容器
stop:
	@echo "停止服务..."
	$(DOCKER_COMPOSE_CMD) down

# 清理
clean: stop
	@echo "清理Docker资源..."
	docker rmi netcup-traffic-throttle-tester:latest 2>/dev/null || true
	docker system prune -f

# 查看日志
logs:
	@echo "查看容器日志..."
	$(DOCKER_COMPOSE_CMD) logs -f

# 进入容器shell
shell:
	@echo "进入容器shell..."
	docker exec -it netcup-tester /bin/bash

# 测试API
test:
	@echo "测试API接口..."
	@echo "健康检查:"
	curl -s http://localhost:51000/health | python3 -m json.tool || echo "请求失败"
	@echo ""
	@echo "测试查询（需要提供真实的IP地址）:"
	@echo "示例: curl 'http://localhost:51000/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae?ipv4IP=YOUR_IP'"

# 查看日志文件信息
logs-info:
	@echo "📋 容器日志文件信息："
	@echo "配置: 最大10MB/文件, 保留3个文件, 总计最大30MB"
	@echo ""
	@if docker ps -q -f name=netcup-tester > /dev/null 2>&1; then \
		echo "当前日志统计:"; \
		docker logs netcup-tester 2>&1 | wc -l | awk '{print "  日志行数: " $$1}'; \
		echo "  健康检查频率: 每10分钟"; \
		echo ""; \
		echo "💡 日志管理命令:"; \
		echo "  查看日志: make logs"; \
		echo "  清理日志: docker logs netcup-tester --since 0s > /dev/null"; \
	else \
		echo "❌ 容器未运行"; \
	fi 