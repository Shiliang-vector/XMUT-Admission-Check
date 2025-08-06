import requests
import json
from util.Notifier import NotifierBase

class PushPlusNotifier(NotifierBase):
    """PushPlus 推送实现"""
    def __init__(self, token, title, content, interval_seconds=10, duration_minutes=10):
        super().__init__(title, content, interval_seconds, duration_minutes)
        self.token = token

    def send_message(self, title, message):
        url = "http://www.pushplus.plus/send"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "token": self.token,
            "title": title,
            "content": message
        }
        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=json.dumps(data, ensure_ascii=False)
            )
            if response.status_code != 200:
                raise Exception(f"状态码：{response.status_code}")
            result = response.json()
            if result.get("code") != 200:
                raise Exception(f"{result.get('msg', '未知错误')}")
        except Exception as e:
            raise Exception(f"PushPlus 推送失败：{str(e)}")


class ServerChanTurboNotifier(NotifierBase):
    """ServerChan Turbo 推送实现"""
    def __init__(self, token, title, content, interval_seconds=10, duration_minutes=10):
        super().__init__(title, content, interval_seconds, duration_minutes)
        self.token = token

    def send_message(self, title, message):
        url = f"https://sctapi.ftqq.com/{self.token}.send"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "title": title,
            "desp": message
        }
        try:
            response = requests.post(
                url=url,
                headers=headers,
                data=json.dumps(data, ensure_ascii=False)
            )
            if response.status_code != 200:
                raise Exception(f"状态码：{response.status_code}")
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"{result.get('message', '未知错误')}")
        except Exception as e:
            raise Exception(f"ServerChan 推送失败：{str(e)}")
