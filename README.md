# XMUT-Admission-Check
# 厦门理工学院录取查询小程序

一个用于查询厦门理工学院录取结果并在录取时自动发送通知的Python小程序。

## 功能说明

- 自动循环查询录取结果
- 支持自定义查询间隔时间
- 录取结果实时推送（支持PushPlus和Server酱 Turbo）
- 自动保存配置信息
- 详细的查询日志记录


## 使用方法

1. 运行程序
2. 首次运行会自动生成`config.json`配置文件
3. 按照提示输入以下信息：
   - 考生号
   - 身份证号
   - 查询间隔时间（秒）
   - 推送方式（可选PushPlus、ServerChan Turbo或不使用推送）
   - 对应推送方式的Token（如选择推送）

4. 程序会自动循环查询，直到获取到录取结果或出现错误

## 推送配置

### PushPlus配置
1. 访问[PushPlus官网](http://www.pushplus.plus/)注册账号
2. 获取个人Token
3. 在程序中选择PushPlus推送方式并输入Token

### ServerChan Turbo配置
1. 访问[ServerChan官网](https://sct.ftqq.com/)注册账号
2. 获取Turbo版Token
3. 在程序中选择ServerChan Turbo推送方式并输入Token

## 项目结构

```
.
├── main.py           # 主程序入口
├── util/
│   ├── Notifier.py   # 推送基类
│   └── Push.py       # 具体推送实现
├── config.json       # 配置文件（自动生成）
└── logs/             # 日志文件目录（自动生成）
```

## 注意事项

- 请确保输入正确的考生号和身份证号
- 合理设置查询间隔，避免过于频繁的请求
- 推送功能仅在检测到录取结果时触发一次
- 日志文件按日期保存在logs目录下，方便查看查询历史

## 免责声明

本程序仅为方便查询录取结果而开发，数据来源为厦门理工学院公开查询接口，请勿用于商业用途。查询结果仅供参考，最终录取结果以学校官方通知为准。
