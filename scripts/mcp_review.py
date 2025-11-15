"""
Diff 获取：在 workflow 里实现了 git diff base...head，能收集修改的代码。
风格检查：你提到 tree-sitter +规则，这部分如果已经接入，就能做 fast check。
文档要求：目前还需要明确如何把需求文档输入到 pipeline（例如作为额外上下文文件）。
相关函数/方法：向量数据库检索还没在 workflow 里体现，但你已经规划了。
LSP 审评意见：如果你能调用 LSP 或静态分析工具（如 pylsp、eslint），就能补充安全/逻辑检查。
结果反馈到 GitHub：你已经实现了 pr.create_issue_comment(...)，结果能自动出现在 PR 页面。
"""
import os
import argparse
from github import Github
from client import Client
import sys

# 把项目根目录加入 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # 参数解析
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--req", required=False)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()

    # 读取 diff 内容
    with open(args.diff_file, "r", encoding="utf-8") as f:
        diff_content = f.read()

    # 读取需求文档（可选）
    requirements = None
    if args.req and os.path.exists(args.req):
        with open(args.req, "r", encoding="utf-8") as f:
            requirements = f.read()

    # 初始化 MCP 客户端
    client = Client()

    # 构建上下文
    context = {
        "files": args.files.split(),
        "diff": diff_content,
        "requirements": requirements,
        "pr_number": args.pr
    }

    # 调用模型
    response = client.query(
        model="code-review-llm",
        context=context,
        prompt="请检查代码风格、潜在 bug、逻辑问题，并比对需求文档，给出改进建议"
    )

    # 将结果写入 GitHub PR Review
    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr = repo.get_pull(int(args.pr))
    pr.create_review(body=f"🤖 MCP Review:\n\n{response}", event="COMMENT")


if __name__ == "__main__":
    main()
