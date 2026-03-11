import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlunparse, urlencode, urlsplit, parse_qsl

RAWJSON = 'raw-json'
FORMDATA = 'form-data'
BINARY = 'binary'


class HttpClient:
    _session = None

    @classmethod
    def _get_session(cls):
        if cls._session is None:
            s = requests.Session()
            retry = Retry(total=4, backoff_factor=0.5,
                          status_forcelist=[429, 502, 503, 504],
                          allowed_methods=["GET", "POST", "PUT", "DELETE"])
            adapter = HTTPAdapter(max_retries=retry)
            s.mount('http://', adapter)
            s.mount('https://', adapter)
            cls._session = s
        return cls._session

    @staticmethod
    def http_get(url, bPrint=True, headers=None, params=None):
        if params is None:
            params = {}

        session = HttpClient._get_session()
        try:
            res = session.get(url, headers=headers, params=params, timeout=(3, 10))

            if bPrint:
                print('http status code:' + str(res.status_code))
            return res
        except Exception as e:
            print(f"[HttpClient] GET failed: {e}")
            return None

    @staticmethod
    def http_post(url, headers=None, body=None, body_type=RAWJSON, bPrint=True):

        session = HttpClient._get_session()
        try:
            if body_type == RAWJSON:
                #res = session.post(url, headers=headers, json=body, timeout=(3, 10), verify=False)
                res = session.post(url, headers=headers, json=body, timeout=(3, 10))
            elif body_type == FORMDATA:
                #res = session.post(url, headers=headers, data=body, timeout=(3, 10), verify=False)
                res = session.post(url, headers=headers, data=body, timeout=(3, 10))
            elif body_type == BINARY:
                #res = session.post(url, headers=headers, files=body, timeout=(3, 10), verify=False)
                res = session.post(url, headers=headers, files=body, timeout=(3, 10))
            else:
                #res = session.post(url, timeout=(3, 10), verify=False)
                res = session.post(url, timeout=(3, 10))

            if bPrint:
                print('http status code:' + str(res.status_code))
            return res
        except Exception as e:
            print(f"[HttpClient] POST failed: {e}")
            return None

    @staticmethod
    def http_delete(url, headers=None, body=None, body_type=RAWJSON, bPrint=True):
        session = HttpClient._get_session()
        try:
            if body_type == RAWJSON:
                res = session.delete(url, headers=headers, json=body, timeout=(3, 10))
            elif body_type == FORMDATA:
                res = session.delete(url, headers=headers, data=body, timeout=(3, 10))
            elif body_type == BINARY:
                res = session.delete(url, headers=headers, files=body, timeout=(3, 10))
            else:
                res = session.delete(url, timeout=(3, 10))

            # # 添加调用：检测http链接
            # check_http_links(url, res)

            if bPrint:
                print('http status code:' + str(res.status_code))
            return res
        except Exception as e:
            print(f"[HttpClient] DELETE failed: {e}")
            return None

    @staticmethod
    def http_put(url, headers=None, body=None, body_type=RAWJSON, bPrint=True):
        session = HttpClient._get_session()
        try:
            if body_type == RAWJSON:
                res = session.put(url, headers=headers, json=body, timeout=(3, 10))
            elif body_type == FORMDATA:
                res = session.put(url, headers=headers, data=body, timeout=(3, 10))
            elif body_type == BINARY:
                res = session.put(url, headers=headers, files=body, timeout=(3, 10))
            else:
                res = session.put(url, timeout=(3, 10))

            # # 添加调用：检测http链接
            # check_http_links(url, res)

            if bPrint:
                print('http status code:' + str(res.status_code))
            return res
        except Exception as e:
            print(f"[HttpClient] PUT failed: {e}")
            return None


    @staticmethod
    def querydict_to_querystr(query_dict):
        """
        将字典转换为url query参数
        :param query_dict:
        :return:
        """
        return urlencode(query_dict)


    @staticmethod
    def makeHttpUrl(netloc, path, query='', scheme='http', params='', fragment=''):
        """
        构造url请求链接
        url全参数格式：'{{scheme}}://{{netloc}}{{path}};{{params}}?{{query}}#{{fragment}}'
        url全参数样例：'https://www.baidu.com/index;user?name=xiebf&passwd=123456#info'
        调用示例：makeHttpUrl('www.baidu.com', '/index', 'name=xiebf&passwd=123456', 'https', 'user', 'info')
        """
        url_parts = [scheme, netloc, path, params, query, fragment]
        return urlunparse(url_parts)

    @staticmethod
    def replaceHost(url, host_new):
        """
        替换url的host
        :param url:
        :param host_new:
        :return:
        """
        us = urlsplit(url)
        host_old = us.netloc
        url = url.replace(host_old, host_new)

        return url

    @staticmethod
    def getRequestParams(url):
        """
        将url链接中的以dict形式返回
        :param url: url链接
        :return: url查询参数dict
        """
        query = urlsplit(url).query
        queryDict = dict(parse_qsl(query))

        return queryDict


if __name__ == '__main__':
    pass
