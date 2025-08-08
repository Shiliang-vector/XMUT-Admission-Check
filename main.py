import requests
import time
import json
import os
import logging
from datetime import datetime
import keyboard
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
        encoding='utf-8'
    )
    return logging.getLogger(__name__)


# 读取配置
def read_config():
    config_path = "config.json"
    default_config = {
        "ksh": "",
        "sfzh": "",
        "interval": 5.0,
        "query_mode": 1,  # 1: 录取时停止 2: EMS单号变化时停止 3: 数据变更时推送
        "push": {
            "method": "none",
            "pushplus_token": "",
            "serverchan_token": ""
        },
        "last_response": None  # 用于存储上次查询结果，检测变化
    }
    if not os.path.exists(config_path):
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        # 确保配置项完整
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


# 通用键盘选择菜单
def keyboard_menu(menu_title, menu_items, current_selection=None):
    """
    通用的键盘选择菜单
    menu_title: 菜单标题
    menu_items: 菜单项列表
    current_selection: 当前选中项索引，用于显示当前配置
    返回选中项的索引
    """
    selected_index = 0

    # 如果有当前选择，设置为初始选中项
    if current_selection is not None and 0 <= current_selection < len(menu_items):
        selected_index = current_selection

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"===== {menu_title} =====")
        print("使用上下方向键选择，按回车键确认，按Ctrl+C返回上一层\n")

        for i, item in enumerate(menu_items):
            if i == selected_index:
                print(f"> {item}")
            else:
                print(f"  {item}")

        print("\n======================")

        # 等待用户按键
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            if event.name == 'up':
                selected_index = (selected_index - 1) % len(menu_items)
            elif event.name == 'down':
                selected_index = (selected_index + 1) % len(menu_items)
            elif event.name == 'enter':
                return selected_index


# 预填信息
def prefill_info(config):
    try:
        print("\n===== 预填信息 =====")
        print("按Ctrl+C返回上一层\n")
        ksh = input(f"请输入考生号（当前：{config['ksh']}）：").strip() or config['ksh']
        sfzh = input(f"请输入身份证号（当前：{config['sfzh']}）：").strip() or config['sfzh']

        config.update({
            "ksh": ksh,
            "sfzh": sfzh
        })

        if save_config(config):
            print("信息已保存\n")
        else:
            print("信息保存失败\n")
        input("按回车键返回菜单...")
    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)
    return config


# 查询配置
def configure_query(config):
    try:
        while True:
            # 配置主菜单
            config_menu = [
                "1. 设置查询间隔时间",
                "2. 选择推送方式",
                "3. 选择查询模式",
                "4. 返回上一层"
            ]

            choice = keyboard_menu("查询配置", config_menu)

            if choice == 0:  # 设置查询间隔
                try:
                    print("\n===== 设置查询间隔 =====")
                    print("按Ctrl+C返回上一层\n")
                    interval_input = input(f"请输入查询间隔（秒，当前：{config['interval']}）：").strip()
                    if interval_input:
                        interval = float(interval_input)
                        if interval > 0:
                            config['interval'] = interval
                            save_config(config)
                            print(f"查询间隔已设置为 {interval} 秒\n")
                        else:
                            print("查询间隔必须大于0\n")
                    else:
                        print("未修改查询间隔\n")
                    input("按回车键返回...")
                except ValueError:
                    print("输入错误，请输入数字！\n")
                    input("按回车键返回...")
                except KeyboardInterrupt:
                    print("\n返回上一层...")
                    time.sleep(1)

            elif choice == 1:  # 选择推送方式
                push_methods = [
                    "1. PushPlus（需输入token）",
                    "2. ServerChan Turbo（需输入token）",
                    "0. 不使用推送"
                ]
                method_map = {0: "pushplus", 1: "serverchan_turbo", 2: "none"}
                current_method = config['push']['method']

                # 确定当前选中的推送方式
                current_selection = 2  # 默认不使用推送
                if current_method == "pushplus":
                    current_selection = 0
                elif current_method == "serverchan_turbo":
                    current_selection = 1

                method_choice = keyboard_menu("选择推送方式", push_methods, current_selection)
                push_method = method_map[method_choice]

                # 获取对应token
                pushplus_token = config['push']['pushplus_token']
                serverchan_token = config['push']['serverchan_token']

                if push_method == "pushplus":
                    try:
                        print("\n===== 设置PushPlus =====")
                        print("按Ctrl+C返回上一层\n")
                        pushplus_token = input(
                            f"请输入PushPlus token（当前：{config['push']['pushplus_token']}）："
                        ).strip() or config['push']['pushplus_token']

                        if not pushplus_token:
                            print("警告：未输入Token，推送功能将禁用")
                            push_method = "none"

                        config['push']['pushplus_token'] = pushplus_token
                        config['push']['method'] = push_method
                        save_config(config)
                        print("配置已保存\n")
                        input("按回车键返回...")
                    except KeyboardInterrupt:
                        print("\n返回上一层...")
                        time.sleep(1)

                elif push_method == "serverchan_turbo":
                    try:
                        print("\n===== 设置ServerChan Turbo =====")
                        print("按Ctrl+C返回上一层\n")
                        serverchan_token = input(
                            f"请输入ServerChan Turbo token（当前：{config['push']['serverchan_token']}）："
                        ).strip() or config['push']['serverchan_token']

                        if not serverchan_token:
                            print("警告：未输入Token，推送功能将禁用")
                            push_method = "none"

                        config['push']['serverchan_token'] = serverchan_token
                        config['push']['method'] = push_method
                        save_config(config)
                        print("配置已保存\n")
                        input("按回车键返回...")
                    except KeyboardInterrupt:
                        print("\n返回上一层...")
                        time.sleep(1)

                else:  # 不使用推送
                    config['push']['method'] = "none"
                    save_config(config)
                    print("已设置为不使用推送\n")
                    input("按回车键返回...")

            elif choice == 2:  # 选择查询模式
                query_modes = [
                    "1. 查询录取，查到录取时停止并推送",
                    "2. 查询录取通知书是否发出（EMS单号不是“暂未发出”时停止并推送）",
                    "3. 检测到数据变更时推送，并继续查询"
                ]

                # 当前模式减1是因为列表索引从0开始
                current_selection = config['query_mode'] - 1
                mode_choice = keyboard_menu("选择查询模式", query_modes, current_selection)
                config['query_mode'] = mode_choice + 1  # 加1转换为实际模式值
                save_config(config)
                print(f"已选择查询模式：{config['query_mode']}\n")
                input("按回车键返回...")

            elif choice == 3:  # 返回上一层
                break

    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)
    return config


# 测试推送效果
def test_push(config):
    try:
        print("\n===== 测试推送效果 =====")
        print("按Ctrl+C返回上一层\n")
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
            title = "测试推送"
            content = "这是一条测试推送，说明推送功能正常"
            if notifier.send(title, content):
                print("推送测试成功，请查收消息\n")
            else:
                print("推送测试失败，请检查配置\n")
        except Exception as e:
            print(f"推送测试失败：{str(e)}\n")

        input("按回车键返回...")
    except KeyboardInterrupt:
        print("\n返回上一层...")
        time.sleep(1)


# 发送通知
def send_notification(notifier, response_json, current_time):
    if not notifier:
        return False

    tdd_data = response_json.get("tdd", {})
    name = tdd_data.get("xm", "未知姓名")
    college = tdd_data.get("xy", "未知学院")
    major = tdd_data.get("result", "未知专业")
    ems_num = tdd_data.get("dh", "未知单号")
    notice_num = tdd_data.get("tzsbh", "未知编号")
    address = tdd_data.get("txdz", "未知地址")

    push_content = (
        f"🎉 厦门理工学院录取信息更新 🎉\n\n"
        f"📌 基本信息\n"
        f"姓名：{name}\n\n"
        f"🎓 录取详情\n"
        f"录取学院：{college}\n"
        f"录取专业：{major}\n\n"
        f"📜 通知书信息\n"
        f"通知书编号：{notice_num}\n"
        f"EMS单号：{ems_num}\n"
        f"通讯地址：{address}\n\n"
        f"⏰ 查询时间：{current_time}"
    )

    try:
        notifier.send(title="厦门理工学院录取信息更新", message=push_content)
        print("推送成功\n")
        return True
    except Exception as e:
        print(f"推送失败: {str(e)}\n")
        return False


# 开始查询
def start_query(config, logger):
    try:
        print("\n===== 开始查询 =====")
        print("按Ctrl+C停止查询并返回上一层\n")

        # 检查必要信息
        if not config['ksh'] or not config['sfzh']:
            print("请先填写考生号和身份证号！\n")
            input("按回车键返回...")
            return

        # 初始化推送器
        notifier = init_notifier(
            config['push']['method'],
            config['push']['pushplus_token'],
            config['push']['serverchan_token']
        )
        method_name = "PushPlus" if config['push']['method'] == "pushplus" else "ServerChan Turbo" if config['push'][
                                                                                                          'method'] != "none" else ""
        if notifier:
            print(f"已启用 {method_name} 推送\n")
        else:
            print("未启用推送功能\n")

        query_count = 0
        has_pushed = False
        last_response = config['last_response']  # 上次查询结果

        try:
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
                        data={"ksh": config['ksh'], "sfzh": config['sfzh']}
                    )
                    current_time = time.strftime("%H:%M:%S")
                    print(f"[{current_time}] 第{query_count}次查询 - 状态码：{response.status_code}")

                    # 解析响应
                    try:
                        response_json = response.json()

                        # 模式3：检测数据变更
                        if config['query_mode'] == 3:
                            if last_response is not None and response_json != last_response:
                                print("检测到数据变更！")
                                # 发送推送
                                if notifier and not has_pushed:
                                    send_notification(notifier, response_json, current_time)
                                    has_pushed = True  # 本次变更只推送一次
                                last_response = response_json
                                config['last_response'] = last_response
                                save_config(config)
                            elif last_response is None:
                                last_response = response_json
                                config['last_response'] = last_response
                                save_config(config)

                        # 检查是否录取
                        if "ok" in response_json and response_json["ok"] is True:
                            tdd_data = response_json.get("tdd", {})
                            name = tdd_data.get("xm", "未知姓名")
                            exam_num = tdd_data.get("ksh", "未知考生号")
                            major = tdd_data.get("result", "未知专业")
                            college = tdd_data.get("xy", "未知学院")
                            ems_num = tdd_data.get("dh", "未知单号")
                            notice_num = tdd_data.get("tzsbh", "未知编号")
                            address = tdd_data.get("txdz", "未知地址")

                            print(f"查询结果：已录取 - {name}（{exam_num}）")
                            print(f"学院：{college}，专业：{major}")
                            print(f"通知书编号：{notice_num}，EMS单号：{ems_num}")
                            print(f"通讯地址：{address}\n")

                            # 模式1：录取时停止并推送
                            if config['query_mode'] == 1:
                                if notifier and not has_pushed:
                                    send_notification(notifier, response_json, current_time)
                                config['last_response'] = response_json
                                save_config(config)
                                print("查询结束（已检测到录取结果）")
                                input("按回车键返回...")
                                break

                            # 模式2：EMS单号不是"暂未发出"时停止
                            if config['query_mode'] == 2 and ems_num != "暂未发出":
                                if notifier and not has_pushed:
                                    send_notification(notifier, response_json, current_time)
                                config['last_response'] = response_json
                                save_config(config)
                                print("查询结束（已检测到EMS单号）")
                                input("按回车键返回...")
                                break

                        # 模式3需要持续运行，重置has_pushed以便下次变更可以推送
                        if config['query_mode'] == 3:
                            has_pushed = False

                        # 等待下一次查询
                        time.sleep(config['interval'])

                    except json.JSONDecodeError:
                        print("响应解析错误，不是有效的JSON格式")
                        logger.error("响应解析错误，不是有效的JSON格式")
                        time.sleep(config['interval'])

                except requests.exceptions.RequestException as e:
                    print(f"查询失败: {str(e)}")
                    logger.error(f"查询失败: {str(e)}")
                    time.sleep(config['interval'])

        except KeyboardInterrupt:
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

    # 菜单选项
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

            # 根据选择执行相应功能
            if selected_index == 0:  # 预填信息
                config = prefill_info(config)
            elif selected_index == 1:  # 查询配置
                config = configure_query(config)
            elif selected_index == 2:  # 开始查询
                start_query(config, logger)
            elif selected_index == 3:  # 测试推送
                test_push(config)
            elif selected_index == 4:  # 退出程序
                print("感谢使用，再见！")
                break
    except KeyboardInterrupt:
        print("\n程序退出")


if __name__ == "__main__":
    try:
        main_menu()
    finally:
        keyboard.unhook_all()

