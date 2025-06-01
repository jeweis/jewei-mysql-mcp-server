# app_config.py
"""
配置模块，用于管理应用程序配置
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置类，用于管理应用程序配置"""
    
    # 数据库配置
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "mysql")
    DB_PORT = os.getenv("DB_PORT", "3306")
    
    # 服务器配置
    SERVER_NAME = os.getenv("SERVER_NAME", "JEWEI-MYSQL-Server")
    
    # 连接字符串
    @property
    def CONNECTION_STRING(self):
        """构建数据库连接字符串"""
        return f"mysql+mysqldb://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# 创建默认配置实例
config = Config()