import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@172.17.12.200:3306/test_platform')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 测试环境默认host
    DEFAULT_HOST = os.getenv('DEFAULT_HOST', '172.17.12.101:9500')