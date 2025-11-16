import asyncio

from src.agent import AgentCore

async def main():
    # 关键：用 await 触发协程执行
    agent = AgentCore()
    result = await agent.review_code("123")
    print("审查结果:", result)

# 3. 运行异步主函数（程序入口）
if __name__ == "__main__":
    asyncio.run(main())  # 启动事件循环，执行协程