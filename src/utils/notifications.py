import time

import schedule


def run_reminder(send_investment_reminder, stop_flag):
    schedule.clear()  # 清除之前的所有任务
    schedule.every().day.at("08:00").do(send_investment_reminder)
    print("Reminder scheduled for 08:00 every day")
    while not stop_flag.is_set():
        schedule.run_pending()
        time.sleep(60 * 1000 * 1000)  # 使用 time.sleep()
    print("Reminder thread stopped")