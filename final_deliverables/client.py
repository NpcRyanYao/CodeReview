import json
import time
from typing import List, Dict, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter

from urllib3.util.retry import Retry


class Client:

    def __init__(
            self,
            api_base_url: str,
            api_key: str,
            model_name: str = "deepseek-chat",
            system_prompt: Optional[str] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        # 基础配置
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout

        # 对话历史：[{role, content, timestamp}, ...]
        self.conversation_history: List[Dict[str, Any]] = []
        if system_prompt:
            self._add_message("system", system_prompt)

        # 简单重试配置（应对网络波动）
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            allowed_methods=["POST"],
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

    def _add_message(self, role: str, content: str) -> None:
        """添加消息到历史（自动补时间戳）"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        })

    def _dict_to_str(self, data_dict: Dict[Any, Any], format_type: str = "pretty") -> str:
        """字典转字符串（支持两种简洁格式）"""
        if format_type == "json":
            return json.dumps(data_dict, ensure_ascii=False, indent=2)
        # 默认 pretty 格式（易读键值对）
        lines = []
        for k, v in data_dict.items():
            if isinstance(v, dict):
                lines.append(f"{k}：")
                lines.append(self._dict_to_str(v, format_type).replace("\n", "\n  "))
            else:
                lines.append(f"{k}：{v}")
        return "\n".join(lines)

    def send(self, content: Union[str, Dict[Any, Any]], format_type: str = "pretty") -> Optional[str]:
        """
        发送消息（支持字符串/字典）
        :param content: 消息内容（字符串或普通字典）
        :param format_type: 字典转换格式（"pretty" 或 "json"）
        :return: 模型回复（失败返回 None）
        """
        # 处理字典内容
        if isinstance(content, dict):
            msg = self._dict_to_str(content, format_type)
        else:
            msg = str(content).strip()

        if not msg:
            print("错误：消息内容不能为空")
            return None

        try:
            # 构建请求数据（包含历史对话）
            messages = [{"role": m["role"], "content": m["content"]} for m in self.conversation_history]
            messages.append({"role": "user", "content": msg})

            response = self.session.post(
                url=f"{self.api_base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"].strip()

            # 记录历史
            self._add_message("user", msg)
            self._add_message("assistant", reply)
            return reply

        except Exception as e:
            print(f"waite：{str(e)}")
            return None

    def get_history(self, role_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """获取对话历史（可选过滤角色）"""
        if not role_filter:
            return self.conversation_history.copy()
        return [m for m in self.conversation_history if m["role"] in role_filter]

    def clear_history(self) -> None:
        """清空对话历史（保留系统提示词）"""
        system_msgs = [m for m in self.conversation_history if m["role"] == "system"]
        self.conversation_history = system_msgs
        print("对话历史已清空（系统提示词保留）")

    def print_history(self, role_filter: Optional[List[str]] = None) -> None:
        """打印对话历史"""
        history = self.get_history(role_filter)
        if not history:
            print("暂无对话历史")
            return
        print("\n" + "=" * 40)
        for m in history:
            role_cn = {"system": "系统", "user": "用户", "assistant": "助手"}[m["role"]]
            print(f"\n【{role_cn}】{m['timestamp']}")
            print(f"内容：{m['content']}")
            print("-" * 30)


# 使用示例
if __name__ == "__main__":
    # 初始化客户端（替换为你的配置）
    client = Client(
        api_base_url="https://api.deepseek.com",  # 本地化模型填 http://localhost:8000 等
        api_key="sk-413bc9536ec04094a4a05e0e1d17bc3b",  # 替换为你的 API 密钥
        model_name="deepseek-chat",
        system_prompt="回答简洁明了"
    )

    # 1. 发送字符串消息
    reply1 = client.send("你好，介绍下自己")
    print(f"助手回复：{reply1}\n")

    # 2. 发送字典消息（自动转为易读格式）
    order_dict = {
        "订单ID": "ORD001",
        "商品": {"名称": "无线耳机", "单价": 899},
        "数量": 1,
        "支付状态": "已支付"
    }
    reply2 = client.send(order_dict, format_type="pretty")
    print(f"助手回复：{reply2}\n")
    reply3 = client.send("把刚才说的再说一遍")

    # 3. 查看对话历史
    client.print_history(role_filter=["user", "assistant"])

    # 4. 清空历史（如需）
    # client.clear_history()