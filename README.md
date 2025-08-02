# Netcup流量限制测试器

通过Netcup WebService API监控VPS流量限制状态，提供HTTP接口查询特定IP的流量限制情况。

## 快速开始

### 1. 创建配置文件
```bash
cp config.json.example config.json
```

### 2. 编辑配置文件
```json
{
    "webhook_path": "/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae",
    "port": 51000,
    "accounts": [
        {
            "loginname": "your_netcup_login",
            "password": "your_netcup_password"
        }
    ]
}
```

### 3. 启动服务
```bash
# Docker方式（推荐）
docker compose up -d

# 或直接运行
python3 netcup_traffic_tester.py
```

### 4. 查询IP状态
```bash
# GET请求（可直接在浏览器中访问）
# 需要传递 ipv4IP=152.53.1.1  参数，就是你要查询流量限制的IPv4公网地址
curl "http://localhost:51000/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae?ipv4IP=152.53.1.1"

# 健康检查
curl http://localhost:51000/health
```

## API响应

**查询成功：**
```json
{
    "ipv4IP": "152.53.1.1",
    "trafficThrottled": false
}
```

**未找到IP：**
```json
{
    "error": "未找到IP 152.53.1.1 的信息"
}
```

## 配置说明

- `webhook_path`: API路径（建议使用复杂的secret路径）
- `port`: 服务端口（默认51000）
- `accounts`: Netcup账户列表，支持多个账户

## 注意事项

- 确保Netcup账户有VPS管理权限
- 系统每5分钟自动更新一次VPS信息
- 支持同时监控多个Netcup账户下的VPS 