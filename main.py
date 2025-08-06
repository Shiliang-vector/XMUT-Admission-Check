import requests
import time
import json
import os
import logging
from datetime import datetime
from util.Notifier import NotifierBase
from util.Push import PushPlusNotifier, ServerChanTurboNotifier


# 配置日志
def setup_logger():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"{log_dir}/query_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        filename=log_filename,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding = 'utf-8'
    )
    return logging.getLogger(__name__)


# 读取配置
def read_config():
    config_path = "config.json"
    default_config = {
        "ksh": "",
        "sfzh": "",
        "interval": 5.0,
        "push": {
            "method": "none",
            "pushplus_token": "",
            "serverchan_token": ""
        }
    }
    if not os.path.exists(config_path):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
        for key in default_config["push"]:
            if key not in config["push"]:
                config["push"][key] = default_config["push"][key]
        return config
    except Exception as e:
        print(f"配置文件错误，使用默认配置: {e}")
        return default_config


# 保存配置
def save_config(config):
    try:
        with open("config.json", 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"配置保存失败: {e}")
        return False


# 初始化推送器
def init_notifier(push_method, pushplus_token, serverchan_token):
    title = "录取通知"
    content = "恭喜！您已成功录取，请及时查看详情。"
    if push_method == "pushplus" and pushplus_token:
        return PushPlusNotifier(
            token=pushplus_token,
            title=title,
            content=content,
            interval_seconds=10,
            duration_minutes=10
        )
    elif push_method == "serverchan_turbo" and serverchan_token:
        return ServerChanTurboNotifier(
            token=serverchan_token,
            title=title,
            content=content,
            interval_seconds=10,
            duration_minutes=10
        )
    return None


def main():
    logger = setup_logger()
    config = read_config()
    print("===== 厦门理工学院录取查询小程序 =====")
    print("提示：直接回车将使用配置文件中的值")

    # 获取考生信息
    ksh = input(f"请输入考生号（当前：{config['ksh']}）：").strip() or config['ksh']
    sfzh = input(f"请输入身份证号（当前：{config['sfzh']}）：").strip() or config['sfzh']
    
    # 处理查询间隔
    while True:
        try:
            interval_input = input(f"请输入查询间隔（秒，当前：{config['interval']}）：").strip()
            interval = float(interval_input) if interval_input else config['interval']
            if interval > 0:
                break
            print("查询间隔必须大于0，请重新输入！")
        except ValueError:
            print("输入错误，请输入数字！")

    # 选择推送方式
    print("\n请选择推送方式（录取时发送通知）：")
    print("1. PushPlus（需输入token）")
    print("2. ServerChan Turbo（需输入token）")
    print("0. 不使用推送")
    push_method_map = {
        "1": "pushplus",
        "2": "serverchan_turbo",
        "0": "none"
    }
    current_method = config['push']['method']
    current_method_display = {
        "pushplus": "PushPlus",
        "serverchan_turbo": "ServerChan Turbo",
        "none": "不使用推送"
    }.get(current_method, "不使用推送")
    print(f"当前配置：{current_method_display}")
    
    # 获取用户选择
    while True:
        push_choice = input("请选择（0-2）：").strip() or (
            "1" if current_method == "pushplus" else
            "2" if current_method == "serverchan_turbo" else "0"
        )
        if push_choice in push_method_map:
            push_method = push_method_map[push_choice]
            break
        print("输入错误，请重新选择！")

    # 获取对应token
    pushplus_token = ""
    serverchan_token = ""
    if push_method == "pushplus":
        pushplus_token = input(
            f"请输入PushPlus token（当前：{config['push']['pushplus_token']}）："
        ).strip() or config['push']['pushplus_token']
        if not pushplus_token:
            print("警告：未输入Token，推送功能将禁用")
            push_method = "none"
    elif push_method == "serverchan_turbo":
        serverchan_token = input(
            f"请输入ServerChan Turbo token（当前：{config['push']['serverchan_token']}）："
        ).strip() or config['push']['serverchan_token']
        if not serverchan_token:
            print("警告：未输入Token，推送功能将禁用")
            push_method = "none"

    # 保存配置
    config.update({
        "ksh": ksh,
        "sfzh": sfzh,
        "interval": interval,
        "push": {
            "method": push_method,
            "pushplus_token": pushplus_token,
            "serverchan_token": serverchan_token
        }
    })
    if save_config(config):
        print("配置已保存\n")
    else:
        print("配置保存失败，将使用当前输入的值\n")

    # 初始化推送器
    notifier = init_notifier(push_method, pushplus_token, serverchan_token)
    method_name = "PushPlus" if push_method == "pushplus" else "ServerChan Turbo" if push_method != "none" else ""
    if notifier:
        print(f"已启用 {method_name} 推送，录取时将自动发送通知\n")
    else:
        print("未启用推送功能\n")

    # 开始查询
    print("===== 开始查询 =====")
    query_count = 0
    has_pushed = False
    while True:
        query_count += 1
        try:
            response = requests.post(
                url="http://58.199.250.102/query",
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Host": "58.199.250.102",
                    "Origin": "http://58.199.250.102",
                    "Referer": "http://58.199.250.102/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/138.0.0.0 Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest"
                },
                data={"ksh": ksh, "sfzh": sfzh}
            )
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] 第{query_count}次查询 - 状态码：{response.status_code}")

            # 解析响应
            try:
                response_json = response.json()
                if "ok" in response_json:
                    if response_json["ok"] is True:
                        # 提取录取信息
                        tdd_data = response_json.get("tdd", {})
                        name = tdd_data.get("xm", "未知姓名")  # 姓名
                        exam_num = tdd_data.get("ksh", "未知考生号")  # 考生号
                        major = tdd_data.get("result", "未知专业")  # 录取专业
                        college = tdd_data.get("xy", "未知学院")  # 录取学院
                        ems_num = tdd_data.get("dh", "未知单号")  # EMS单号
                        notice_num = tdd_data.get("tzsbh", "未知编号")  # 通知书编号
                        address = tdd_data.get("txdz", "未知地址")  # 通讯地址（null时显示"未填写"）
                        print(f"查询结果：已录取 - {name}（{exam_num}）")
                        print(f"学院：{college}，专业：{major}")
                        print(f"通知书编号：{notice_num}，EMS单号：{ems_num}")
                        print(f"通讯地址：{address}\n")

                        # 录取且未推送过 → 触发推送
                        if not has_pushed and notifier:
                            try:
                                # 构建包含所有信息的推送内容
                                push_content = (
                                    f"🎉 厦门理工学院录取成功通知 🎉\n\n"
                                    f"📌 基本信息\n"
                                    f"姓名：{name}\n"
                                    #f"考生号：{exam_num}\n"
                                    #f"身份证号：{sfzh}\n\n"
                                    #f"🎓 录取详情\n"
                                    f"录取学院：{college}\n"
                                    f"录取专业：{major}\n\n"
                                    f"📜 通知书信息\n"
                                    f"通知书编号：{notice_num}\n"
                                    f"EMS单号：{ems_num}\n"
                                    f"通讯地址：{address}\n\n"
                                    f"⏰ 查询时间：{current_time}"
                                )
                                # 发送推送
                                notifier.send(title="厦门理工学院录取成功通知", message=push_content)
                                # 打印推送内容
                                #rint(f"\n【{method_name}推送内容】：")
                                #print(push_content)
                                has_pushed = True
                                break
                            except Exception as e:
                                print(f"推送失败：{e}")
                                logger.error(f"{method_name} 推送失败：{e}")
                                break
                        else:
                            print("查询结束")
                            break
                    else:
                        print("查询结果：未录取或未到时间")
            except json.JSONDecodeError:
                error_msg = "响应内容不是有效JSON，无法解析"
                print(error_msg)
                logger.error(error_msg)

            print(f"响应内容：{response.text}\n")

            if response.status_code != 200:
                error_msg = f"非200状态码（{response.status_code}），查询结束"
                print(error_msg)
                logger.error(error_msg)
                break

            time.sleep(interval)

        except Exception as e:
            error_msg = f"查询出错：{e}，查询结束"
            print(error_msg)
            logger.error(error_msg)
            break


if __name__ == "__main__":
    main()
