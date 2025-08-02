#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request
import logging
from netcup_webservice import NetcupWebservice

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NetcupTrafficThrottleTester:
    def __init__(self):
        # 固定读取脚本同目录的config.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(script_dir, 'config.json')
        
        # 数据缓存 - 存储所有VPS的信息
        # 格式: {"ipv4_ip": {"ipv4IP": "xxx", "trafficThrottled": bool}}
        self.cached_data = {}
        
        # 加载配置
        config = self.load_config()
        self.webhook_path = config.get('webhook_path', '/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae')
        self.port = config.get('port', 51000)
        self.accounts = config.get('accounts', [])
        
        # 创建Flask应用
        self.app = Flask(__name__)
        self.setup_routes()
        
        # 启动数据收集线程
        self.data_thread = threading.Thread(target=self.data_collection_loop, daemon=True)
        self.data_thread.start()
        
        logger.info(f"NetcupTrafficThrottleTester初始化完成")
        logger.info(f"Webhook路径: {self.webhook_path}")
        logger.info(f"端口: {self.port}")
        logger.info(f"配置文件: {self.config_file}")
        logger.info(f"加载了 {len(self.accounts)} 个账户")

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        except FileNotFoundError:
            logger.error(f"配置文件 {self.config_file} 不存在，请创建配置文件")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"配置文件JSON格式错误: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件时发生错误: {e}")
            return {}

    def setup_routes(self):
        """设置Flask路由"""
        @self.app.route(self.webhook_path, methods=['GET', 'POST'])
        def webhook():
            try:
                # 获取ipv4IP参数
                ipv4_ip = request.args.get('ipv4IP')
                if not ipv4_ip:
                    return jsonify({"error": "缺少ipv4IP参数"}), 400
                
                # 从缓存中查找对应的数据
                if ipv4_ip in self.cached_data:
                    return jsonify(self.cached_data[ipv4_ip])
                else:
                    return jsonify({"error": f"未找到IP {ipv4_ip} 的信息"}), 404
                    
            except Exception as e:
                logger.error(f"处理webhook请求时发生错误: {e}")
                return jsonify({"error": "内部服务器错误"}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                "status": "ok", 
                "timestamp": datetime.now().isoformat(),
                "total_servers": len(self.cached_data)
            })

    def get_vps_info_from_account(self, account):
        """从单个账户获取VPS信息"""
        vps_data = {}
        try:
            # 初始化netcup客户端
            client = NetcupWebservice(
                loginname=account['loginname'], 
                password=account['password']
            )
            
            # 获取所有vserver
            vservers = client.get_vservers()
            logger.info(f"账户 {account['loginname']} 有 {len(vservers)} 个VPS")
            
            # 获取每个vserver的详细信息
            for vserver_name in vservers:
                try:
                    vserver_info = client.get_vserver_information(vserver_name)
                    
                    # 提取serverInterfaces中的ipv4IP和trafficThrottled
                    # 根据task.md中的数据结构示例：serverInterfaces是一个数组，每个接口有ipv4IP(数组)和trafficThrottled(布尔值)
                    if 'serverInterfaces' in vserver_info and vserver_info['serverInterfaces']:
                        # 读取第一个接口的信息（按照task.md的要求）
                        interface = vserver_info['serverInterfaces'][0]
                        
                        try:
                            # 根据task.md示例，直接访问对象属性
                            # ipv4IP: ['152.53.197.30'] - 数组
                            # trafficThrottled: False - 布尔值
                            ipv4_ips = getattr(interface, 'ipv4IP', [])
                            traffic_throttled = getattr(interface, 'trafficThrottled', False)
                            
                            logger.debug(f"从接口获取到: ipv4IP={ipv4_ips}, trafficThrottled={traffic_throttled}")
                            
                            # 确保ipv4_ips是列表
                            if not isinstance(ipv4_ips, list):
                                ipv4_ips = [ipv4_ips] if ipv4_ips else []
                            
                            # 为每个IPv4地址创建记录
                            for ipv4_ip in ipv4_ips:
                                if ipv4_ip:  # 确保IP不为空
                                    vps_data[ipv4_ip] = {
                                        "ipv4IP": ipv4_ip,
                                        "trafficThrottled": traffic_throttled
                                    }
                                    logger.info(f"成功添加VPS信息: {ipv4_ip} -> trafficThrottled: {traffic_throttled}")
                        
                        except Exception as attr_error:
                            logger.error(f"访问接口属性时出错: {attr_error}")
                            logger.debug(f"接口对象类型: {type(interface)}")
                            
                            # 打印接口对象的详细信息用于调试
                            try:
                                if hasattr(interface, '__dict__'):
                                    logger.debug(f"接口对象属性: {interface.__dict__}")
                                else:
                                    logger.debug(f"接口对象内容: {interface}")
                            except:
                                logger.debug("无法打印接口对象详情")
                            continue
                
                except Exception as e:
                    logger.error(f"获取VPS {vserver_name} 信息失败: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"从账户 {account['loginname']} 获取VPS信息失败: {e}")
        
        return vps_data

    def update_cached_data(self):
        """更新缓存的数据"""
        try:
            new_data = {}
            
            # 遍历所有配置的账户
            for account in self.accounts:
                if 'loginname' not in account or 'password' not in account:
                    logger.warning(f"账户配置不完整，跳过: {account}")
                    continue
                
                logger.info(f"正在从账户 {account['loginname']} 获取VPS信息...")
                account_data = self.get_vps_info_from_account(account)
                new_data.update(account_data)
            
            # 更新缓存
            self.cached_data = new_data
            logger.info(f"数据更新成功，共缓存 {len(self.cached_data)} 个VPS IP信息")
            
            # 打印缓存的IP列表用于调试
            if self.cached_data:
                logger.info(f"缓存的IP列表: {list(self.cached_data.keys())}")
            
        except Exception as e:
            logger.error(f"更新缓存数据时发生错误: {e}")

    def data_collection_loop(self):
        """数据收集循环，每5分钟执行一次"""
        logger.info("数据收集线程已启动")
        
        # 立即执行一次数据更新
        self.update_cached_data()
        
        while True:
            try:
                time.sleep(300)  # 5分钟 = 300秒
                self.update_cached_data()
            except Exception as e:
                logger.error(f"数据收集循环中发生错误: {e}")
                time.sleep(60)  # 发生错误时等待1分钟后重试

    def run(self):
        """启动Flask应用"""
        logger.info(f"启动Web服务，端口: {self.port}")
        logger.info(f"Webhook URL: http://localhost:{self.port}{self.webhook_path}")
        logger.info(f"使用方法: GET/POST {self.webhook_path}?ipv4IP=YOUR_IP")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)

def main():
    tester = NetcupTrafficThrottleTester()
    tester.run()

if __name__ == '__main__':
    main() 