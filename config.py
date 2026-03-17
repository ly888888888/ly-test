import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@172.17.12.200:3306/test_platform')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 测试环境默认host
    DEFAULT_HOST = os.getenv('DEFAULT_HOST', '172.17.12.101:9500')
    # 鏉冮檺鎺у埗
    AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'true').lower() in ['1', 'true', 'yes', 'on']
    TOKEN_EXPIRES_HOURS = int(os.getenv('TOKEN_EXPIRES_HOURS', '24'))
    ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
