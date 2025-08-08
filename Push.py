import requests
import json
from Notifier import NotifierBase

def _send_post_request(url, headers, data, success_code):
    """通用POST请求发送函数，提取重复逻辑"""
    try:
        response = requests.post(
            url=url,
            headers=headers,
            data=json.dumps(data, ensure_ascii=False)
        )
        if response.status_code != 200:
            raise Exception(f"状态码：{response.status_code}")
        result = response.json()
        if result.get("code") != success_code:
            error_msg = result.get("msg") or result.get("message") or "未知错误"
            raise Exception(error_msg)
    except Exception as e:
        raise e  # 让调用方处理具体错误信息


class PushPlusNotifier(NotifierBase):
    """PushPlus 推送实现"""
    def __init__(self, token, title, content, interval_seconds=10, duration_minutes=10):
        super().__init__(title, content, interval_seconds, duration_minutes)
        self.token = token

    def send_message(self, title, message):
        try:
            _send_post_request(
                url="http://www.pushplus.plus/send",
                headers={"Content-Type": "application/json; charset=utf-8"},
                data={"token": self.token, "title": title, "content": message},
                success_code=200
            )
        except Exception as e:
            raise Exception(f"PushPlus 推送失败：{str(e)}")


class ServerChanTurboNotifier(NotifierBase):
    """ServerChan Turbo 推送实现"""
    def __init__(self, token, title, content, interval_seconds=10, duration_minutes=10):
        super().__init__(title, content, interval_seconds, duration_minutes)
        self.token = token

    def send_message(self, title, message):
        try:
            _send_post_request(
                url=f"https://sctapi.ftqq.com/{self.token}.send",
                headers={"Content-Type": "application/json; charset=utf-8"},
                data={"title": title, "desp": message},
                success_code=0
            )
        except Exception as e:
            raise Exception(f"ServerChan 推送失败：{str(e)}")