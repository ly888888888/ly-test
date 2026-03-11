import pymysql

class TestDB:
    test_db_host = '172.17.12.200'
    test_db_port = 3306
    test_db_user = "root"
    test_db_pwd = "root"

    @classmethod
    def get_connection(cls):
        """封装数据库连接，返回一个 MySQL 连接对象"""
        conn = pymysql.connect(
            host=cls.test_db_host,
            port=cls.test_db_port,
            user=cls.test_db_user,
            password=cls.test_db_pwd,
            charset='utf8mb4'     # 使用 utf8mb4 支持完整 Unicode
        )
        return conn


class TestAssert:
    success = True
    fail = False

class TestResult:
    PASS = 'PASS'
    NOTICE = 'NOTICE'
    WARNING = 'WARNING'
    FAIL = 'FAIL'
    LOST = 'LOST'

class TestLogInfo:
    api_id = 0
    case_desc = ''
    url = ''
    http_status = 0
    test_result = ''
    error_info = ''



