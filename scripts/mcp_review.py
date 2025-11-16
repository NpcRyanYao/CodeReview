"""
Diff 获取：在 workflow 里实现了 git diff base...head，能收集修改的代码。
风格检查：你提到 tree-sitter +规则，这部分如果已经接入，就能做 fast check。
文档要求：目前还需要明确如何把需求文档输入到 pipeline（例如作为额外上下文文件）。
相关函数/方法：向量数据库检索还没在 workflow 里体现，但你已经规划了。
LSP 审评意见：如果你能调用 LSP 或静态分析工具（如 pylsp、eslint），就能补充安全/逻辑检查。
结果反馈到 GitHub：你已经实现了 pr.create_issue_comment(...)，结果能自动出现在 PR 页面。
"""
import sys
import os

# 把项目根目录加入 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from github import Github
from client import Client


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--req", required=False)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()

    # 读取 diff 内容
    with open(args.diff_file, "r", encoding="utf-8") as f:
        diff_content = f.read()

    # 读取需求文档
    # 通过 --req requirements.md 参数，把需求文档传入。
    # 脚本会读取文档内容，并放进 context["requirements"]。
    # 然后在调用 LLM 时，文档内容会作为上下文一起传入。
    requirements = None
    if args.req and os.path.exists(args.req):
        with open(args.req, "r", encoding="utf-8") as f:
            requirements = f.read()

    client = Client()

    # 构建上下文
    context = {
        "files": args.files.split(),
        "diff": diff_content,
        "requirements": requirements,
        "pr_number": args.pr
    }

    # 整体评审结果
    response = client.query(
        model="code-review-llm",
        context=context,
        prompt="请检查代码风格、潜在 bug、逻辑问题，并比对需求文档，给出改进建议"
    )

    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr = repo.get_pull(int(args.pr))

    # 1️⃣ 保留 Conversation 评论
    pr.create_issue_comment(f"🤖 MCP Review:\n\n{response}")

    # 2️⃣ 分文件精确评审
    comments = []
    for file in context["files"]:
        file_review = client.query(
            model="code-review-llm",
            context={"file": file, "requirements": requirements},
            prompt=f"请针对文件 {file} 的改动进行精确评审，指出问题和改进建议"
        )
        # 注意：position 是 diff 中的行号，这里简单挂在文件开头
        comments.append({
            "path": file,
            "position": 1,
            "body": f"🤖 文件 {file} 评审:\n{file_review}"
        })

    if comments:
        pr.create_review(
            body="🤖 分文件精确评审结果",
            event="COMMENT",
            comments=comments
        )

    print("✅ 已写回 Conversation 评论和分文件评审")


if __name__ == "__main__":
    main()
