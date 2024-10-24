import argparse
import time


def parse_arguments():
    parser = argparse.ArgumentParser(description="Investment App")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--login", help="Login to PushPlus with token", metavar="TOKEN")
    parser.add_argument("--estimate", action="store_true", help="Estimate today's investment")
    parser.add_argument("--start-reminder", action="store_true", help="Start investment reminder")
    return parser.parse_args()


def run_cli(app, args):
    if args.login:
        if app.pushplus_login(args.login):
            print("PushPlus登录成功")
        else:
            print("PushPlus登录失败")

    # 如果没有显式登录，尝试使用保存的 token 自动登录
    if not app.is_logged_in:
        app.auto_login()

    if args.estimate:
        if app.is_logged_in:
            result = app.estimate_today_investment()
            print(result)
        else:
            print("错误: 请先登录PushPlus")

    if args.start_reminder:
        if app.is_logged_in:
            result = app.start_reminder()
            if result:
                print("定投提醒功能已启动")
                # Keep the script running
                while True:
                    time.sleep(60)  # 使用 time.sleep()，每分钟检查一次
            else:
                print("定投提醒功能启动失败或已在运行中")
        else:
            print("错误: 请先登录PushPlus")
