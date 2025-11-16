# client.py
# client.py
class Client:
    def query(self, model, context, prompt):
        files = context.get("files") or context.get("file") or "未提供文件"
        return f"[模拟结果] 模型 {model} 收到上下文 {files}，提示词：{prompt}"

# TODO: 测试 PR 流程


def FunctionName_2():
    print("t121345")
