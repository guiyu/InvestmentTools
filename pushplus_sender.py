import requests


class PushPlusSender:
    def __init__(self, token):
        self.token = token
        self.base_url = "http://www.pushplus.plus/send"

    def send_message(self, title, content, template="html"):
        data = {
            "token": self.token,
            "title": title,
            "content": content,
            "template": template
        }

        response = requests.post(self.base_url, json=data)

        if response.status_code == 200:
            result = response.json()
            if result["code"] == 200:
                print("消息发送成功")
                return True
            else:
                print(f"消息发送失败: {result['msg']}")
                return False
        else:
            print(f"请求失败: {response.status_code}")
            return False


# 使用示例
if __name__ == "__main__":
    token = ""
    sender = PushPlusSender(token)
    sender.send_message("测试标题", "这是一条测试消息")