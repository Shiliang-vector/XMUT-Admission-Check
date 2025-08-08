import json
import logging
import os
import sys
import time
from datetime import datetime

import keyboard
import requests

from Notifier import NotifierBase
from Push import PushPlusNotifier, ServerChanTurboNotifier


# 清除屏幕
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


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
        encoding='utf-8'
    )
    return logging.getLogger(__name__)


# 读取配置（递归合并默认配置）
def read_config():
    config_path = "config.json"
    default_config = {
        "ksh": "",
        "sfzh": "",
        "interval": 5.0,
        "query_mode": 1,
        "push": {
            "method": "none",
            "pushplus_token": "",
            "serverchan_token": ""
        },
        "last_response": None
    }

    # 递归合并配置（补充缺失键，不覆盖已有键）
    def merge_dict(target, source):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                merge_dict(target[k], v)
            else:
                target.setdefault(k, v)

    if not os.path.exists(config_path):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        merge_dict(config, default_config)
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
def init_notifier(push_method, pushplus_token, serverchan_token) -> None | NotifierBase:
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


# 键盘选择菜单
def keyboard_menu(menu_title, menu_items, current_selection=None):
    """菜单：上下键移动，Enter确认，Esc返回-1"""
    selected_index = 0
    if current_selection is not None and 0 <= current_selection < len(menu_items):
        selected_index = current_selection

    key_actions = {
        'up': lambda: (selected_index - 1) % len(menu_items),
        'down': lambda: (selected_index + 1) % len(menu_items),
        'enter': lambda: 'confirm',
        'esc': lambda: 'exit'
    }

    while True:
        clear_screen()
        print(f"===== {menu_title} =====")
        print("使用上下方向键选择，按回车键确认，按ESC键返回\n")

        for i, item in enumerate(menu_items):
            print(f"> {item}" if i == selected_index else f"  {item}")

        print("\n======================")

        event = keyboard.read_event(suppress=True)
        if event.event_type == keyboard.KEY_DOWN:
            action = key_actions.get(event.name)
            if not action:
                continue
            result = action()
            if result == 'confirm':
                return selected_index
            elif result == 'exit':
                return -1
            else:
                selected_index = result


# 格式化部分隐藏显示
def format_partial_hide(value):
    if not value or len(value) <= 7:
        return value
    return f"{value[:3]}{'*' * (len(value) - 7)}{value[-4:]}"


# 通用输入验证函数
def input_and_validate(prompt, current_value, validator, formatter=lambda x: x):
    """
    通用输入验证函数
    :param prompt: 输入提示
    :param current_value: 当前值
    :param validator: 验证函数（返回 (是否有效, 错误信息)）
    :param formatter: 显示当前值的格式化函数
    :return: 新值（若有效）或原值
    """
    display = formatter(current_value) if current_value else "无"
    new_value = input(f"{prompt}（当前：{display}）：").strip()
    if not new_value:
        return current_value  # 未输入则保持原值
    is_valid, error_msg = validator(new_value)
    if is_valid:
        return new_value
    print(error_msg)
    return current_value


# 预填信息
def prefill_info(config):
    try:
        # 考生号验证器
        def validate_ksh(value):
            return True, "" if len(value) == 14 and value.isdigit() else (False, "考生号格式不正确，应为14位数字！")

        # 身份证号验证器
        def validate_sfzh(value):
            upper_val = value.upper()
            if len(upper_val) == 18 and upper_val[:-1].isdigit() and (upper_val[-1].isdigit() or upper_val[-1] == 'X'):
                return True, ""
            return False, "身份证号格式不正确，应为18位数字（最后一位可为X）！"

        while True:
            ksh_status = format_partial_hide(config['ksh']) if config['ksh'] else "未填写"
            sfzh_status = format_partial_hide(config['sfzh']) if config['sfzh'] else "未填写"

            info_menu = [
                f"1. 考生号 - {ksh_status}",
                f"2. 身份证号 - {sfzh_status}",
                "3. 返回上一层"
            ]

            choice = keyboard_menu("预填信息", info_menu)
            if choice == -1 or choice == 2:
                print("\n返回上一层...")
                time.sleep(1)
                break

            if choice == 0:  # 修改考生号
                print("\n===== 修改考生号 =====")
                print("按ESC键取消修改，输入完成后按回车键确认\n")
                config['ksh'] = input_and_validate(
                    "请输入考生号",
                    config['ksh'],
                    validate_ksh,
                    format_partial_hide
                )
                save_config(config)
                print(f"考生号已更新为：{format_partial_hide(config['ksh'])}\n")
                input("按回车键返回...")

            elif choice == 1:  # 修改身份证号
                print("\n===== 修改身份证号 =====")
                print("按ESC键取消修改，输入完成后按回车键确认\n")
                new_sfzh = input_and_validate(
                    "请输入身份证号",
                    config['sfzh'],
                    validate_sfzh,
                    format_partial_hide
                )
                config['sfzh'] = new_sfzh.upper()
                save_config(config)
                print("身份证号已更新\n")
                input("按回车键返回...")

    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)
    return config


# 查询配置
def configure_query(config):
    try:
        # 查询间隔验证器
        def validate_interval(value):
            try:
                interval = float(value)
                return (True, "") if interval > 0 else (False, "查询间隔必须大于0")
            except ValueError:
                return False, "输入错误，请输入有效的数字！"

        while True:
            config_menu = [
                "1. 设置查询间隔时间",
                "2. 选择推送方式",
                "3. 选择查询模式",
                "4. 返回上一层"
            ]

            choice = keyboard_menu("查询配置", config_menu)
            if choice == -1 or choice == 3:
                print("\n返回上一层...")
                time.sleep(1)
                break

            if choice == 0:  # 设置查询间隔
                print("\n===== 设置查询间隔 =====")
                print("按ESC键取消，输入完成后按回车键确认\n")
                config['interval'] = float(input_and_validate(
                    "请输入查询间隔（秒）",
                    str(config['interval']),
                    validate_interval
                ))
                save_config(config)
                print(f"查询间隔已设置为 {config['interval']} 秒\n")
                input("按回车键返回...")

            elif choice == 1:  # 选择推送方式
                push_methods = [
                    "1. PushPlus（需输入token）",
                    "2. ServerChan Turbo（需输入token）",
                    "0. 不使用推送"
                ]
                method_map = {0: "pushplus", 1: "serverchan_turbo", 2: "none"}
                current_method = config['push']['method']
                current_selection = 2 if current_method == "none" else 0 if current_method == "pushplus" else 1

                method_choice = keyboard_menu("选择推送方式", push_methods, current_selection)
                if method_choice == -1:
                    continue

                push_method = method_map[method_choice]
                if push_method == "pushplus":
                    print("\n===== 设置PushPlus =====")
                    token = input(f"请输入PushPlus token（当前：{config['push']['pushplus_token']}）：").strip()
                    config['push']['pushplus_token'] = token or config['push']['pushplus_token']
                    config['push']['method'] = push_method if config['push']['pushplus_token'] else "none"
                    save_config(config)
                    print("配置已保存\n")
                    input("按回车键返回...")

                elif push_method == "serverchan_turbo":
                    print("\n===== 设置ServerChan Turbo =====")
                    token = input(f"请输入ServerChan Turbo token（当前：{config['push']['serverchan_token']}）：").strip()
                    config['push']['serverchan_token'] = token or config['push']['serverchan_token']
                    config['push']['method'] = push_method if config['push']['serverchan_token'] else "none"
                    save_config(config)
                    print("配置已保存\n")
                    input("按回车键返回...")

                else:
                    config['push']['method'] = "none"
                    save_config(config)
                    print("已设置为不使用推送\n")
                    input("按回车键返回...")

            elif choice == 2:  # 选择查询模式
                query_modes = [
                    "1. 查询录取，查到录取时停止并推送",
                    "2. 查询录取通知书是否发出（EMS单号变化时停止）",
                    "3. 检测到数据变更时推送，并继续查询"
                ]
                current_selection = config['query_mode'] - 1
                mode_choice = keyboard_menu("选择查询模式", query_modes, current_selection)
                if mode_choice == -1:
                    continue
                config['query_mode'] = mode_choice + 1
                save_config(config)
                print(f"已选择查询模式：{config['query_mode']}\n")
                input("按回车键返回...")

    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)
    return config


# 测试推送效果
def test_push(config):
    try:
        print("\n===== 测试推送效果 =====")
        notifier = init_notifier(
            config['push']['method'],
            config['push']['pushplus_token'],
            config['push']['serverchan_token']
        )

        if not notifier:
            print("未配置有效的推送方式，请先在查询配置中设置\n")
            input("按回车键返回...")
            return

        try:
            if notifier.send("测试推送", "这是一条测试推送，说明推送功能正常"):
                print("推送测试成功，请查收消息\n")
            else:
                print("推送测试失败，请检查配置\n")
        except Exception as e:
            print(f"推送测试失败：{str(e)}\n")

        input("按回车键返回...")
    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)


# 发送通知（用字段列表简化内容生成）
def send_notification(notifier: None | NotifierBase, response_json, current_time):
    if not notifier:
        return False

    tdd_data = response_json.get("tdd", {})
    # 定义需要提取的字段（键名: (显示名, 默认值)）
    fields = [
        ("xm", "姓名", "未知姓名"),
        ("xy", "录取学院", "未知学院"),
        ("result", "录取专业", "未知专业"),
        ("tzsbh", "通知书编号", "未知编号"),
        ("dh", "EMS单号", "未知单号"),
        ("txdz", "通讯地址", "未知地址"),
    ]
    info_lines = [f"{label}：{tdd_data.get(key, default)}" for key, label, default in fields]

    push_content = (
        f"🎉 厦门理工学院录取信息更新 🎉\n\n"
        f"📌 基本信息\n"
        f"{info_lines[0]}\n\n"  # 姓名
        f"🎓 录取详情\n"
        f"{info_lines[1]}\n"    # 学院
        f"{info_lines[2]}\n\n"  # 专业
        f"📜 通知书信息\n"
        f"{info_lines[3]}\n"    # 通知书编号
        f"{info_lines[4]}\n"    # EMS单号
        f"{info_lines[5]}\n\n"  # 地址
        f"⏰ 查询时间：{current_time}"
    )

    try:
        notifier.send(title="厦门理工学院录取信息更新", message=push_content)
        print("推送成功\n")
        return True
    except Exception as e:
        print(f"推送失败: {str(e)}\n")
        return False


# 拆分：发送查询请求
def fetch_data(ksh, sfzh):
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
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        raise Exception(f"查询失败: {str(e)}")


# 拆分：处理查询模式逻辑
def handle_query_mode(response_json, config, last_response, notifier, current_time):
    tdd_data = response_json.get("tdd", {})
    should_stop = False

    if config['query_mode'] == 3:
        # 模式3：检测数据变更
        if last_response is not None and response_json != last_response:
            print("检测到数据变更！")
            send_notification(notifier, response_json, current_time)
            last_response = response_json
        elif last_response is None:
            last_response = response_json
        return last_response, False  # 不停止查询

    if "ok" in response_json and response_json["ok"] is True:
        # 打印录取信息
        print(f"查询结果：已录取 - {tdd_data.get('xm', '未知姓名')}（{tdd_data.get('ksh', '未知考生号')}）")
        print(f"学院：{tdd_data.get('xy', '未知学院')}，专业：{tdd_data.get('result', '未知专业')}")
        print(f"通知书编号：{tdd_data.get('tzsbh', '未知编号')}，EMS单号：{tdd_data.get('dh', '未知单号')}")
        print(f"通讯地址：{tdd_data.get('txdz', '未知地址')}\n")

        # 模式1：查到录取停止
        if config['query_mode'] == 1:
            send_notification(notifier, response_json, current_time)
            should_stop = True
        # 模式2：EMS单号非"暂未发出"时停止
        elif config['query_mode'] == 2 and tdd_data.get('dh', "暂未发出") != "暂未发出":
            send_notification(notifier, response_json, current_time)
            should_stop = True

    return response_json, should_stop


# 开始查询（主逻辑拆分后更简洁）
def start_query(config, logger):
    try:
        print("\n===== 开始查询 =====")
        print("按ESC键停止查询并返回上一层\n")

        if not config['ksh'] or not config['sfzh']:
            print("请先填写考生号和身份证号！\n")
            input("按回车键返回...")
            return

        notifier = init_notifier(
            config['push']['method'],
            config['push']['pushplus_token'],
            config['push']['serverchan_token']
        )
        method_name = {
            "pushplus": "PushPlus",
            "serverchan_turbo": "ServerChan Turbo",
            "none": ""
        }.get(config['push']['method'], "")
        print(f"已启用 {method_name} 推送\n" if method_name else "未启用推送功能\n")

        query_count = 0
        last_response = config['last_response']
        stop_flag = False

        def on_esc_press(event):
            nonlocal stop_flag
            if event.name == 'esc' and event.event_type == keyboard.KEY_DOWN:
                stop_flag = True

        keyboard.on_press(on_esc_press)

        try:
            while not stop_flag:
                query_count += 1
                current_time = time.strftime("%H:%M:%S")
                try:
                    response = fetch_data(config['ksh'], config['sfzh'])
                    print(f"[{current_time}] 第{query_count}次查询 - 状态码：{response.status_code}")

                    try:
                        response_json = response.json()
                        last_response, should_stop = handle_query_mode(
                            response_json, config, last_response, notifier, current_time
                        )
                        config['last_response'] = last_response
                        save_config(config)

                        if should_stop:
                            print("查询结束（已检测到目标结果）")
                            input("按回车键返回...")
                            break

                    except json.JSONDecodeError:
                        print("响应解析错误，不是有效的JSON格式")
                        logger.error("响应解析错误，不是有效的JSON格式")

                except Exception as e:
                    print(f"查询失败: {str(e)}")
                    logger.error(f"查询失败: {str(e)}")

                # 带ESC检测的等待
                for _ in range(int(config['interval'] * 10)):
                    if stop_flag:
                        break
                    time.sleep(0.1)

        finally:
            keyboard.unhook_all()
            if stop_flag:
                print("\n用户终止查询")
                config['last_response'] = last_response
                save_config(config)
                input("按回车键返回...")

    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)


# 主菜单
def main_menu():
    logger = setup_logger()
    config = read_config()

    menu_items = [
        "1. 预填信息 - 填写考生号以及身份证号",
        "2. 查询配置 - 设置查询间隔、推送方式、查询模式",
        "3. 开始查询",
        "4. 测试推送效果 - 发送一次测试推送",
        "5. 退出程序"
    ]

    try:
        while True:
            selected_index = keyboard_menu("厦门理工学院录取查询小程序", menu_items)
            if selected_index == -1:
                print("\n确定要退出程序吗？(y/n)")
                if input().strip().lower() == 'y':
                    print("感谢使用，再见！")
                    break
                continue

            if selected_index == 0:
                config = prefill_info(config)
            elif selected_index == 1:
                config = configure_query(config)
            elif selected_index == 2:
                start_query(config, logger)
            elif selected_index == 3:
                test_push(config)
            elif selected_index == 4:
                print("感谢使用，再见！")
                break
    except KeyboardInterrupt:
        print("\n程序退出")


if __name__ == "__main__":
    try:
        main_menu()
    finally:
        keyboard.unhook_all()
        sys.exit(0)