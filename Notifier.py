import time


class NotifierBase:
    """推送通知基类，定义通用逻辑，具体推送由子类实现"""

    def __init__(self, title, content, interval_seconds=10, duration_minutes=10):
        """初始化推送参数"""
        self.title = title
        self.content = content
        self.interval_seconds = interval_seconds
        self.duration_minutes = duration_minutes
        self.last_sent_time = 0  # 上次推送时间（时间戳）
        self.start_time = time.time()  # 推送功能启动时间

    def can_send(self):
        """判断是否可以推送（控制频率和有效时长）"""
        current_time = time.time()
        return (current_time - self.last_sent_time >= self.interval_seconds and
                current_time - self.start_time <= self.duration_minutes * 60)

    def send(self, title=None, message=None):
        """对外接口：发送推送（自动检查是否符合推送条件）"""
        title = title or self.title
        message = message or self.content

        if self.can_send():
            self.send_message(title, message)
            self.last_sent_time = time.time()
            return True
        return False

    def send_message(self, title, message):
        """抽象方法：具体推送逻辑由子类实现"""
        raise NotImplementedError("子类必须实现 send_message 方法")
