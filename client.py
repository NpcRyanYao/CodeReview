# client.py
class Client:
    def query(self, model, context, prompt):
        return f"[模拟结果] 模型 {model} 收到上下文 {context['files']}，提示词：{prompt}"
