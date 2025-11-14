import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
from github import Github
from client import Client
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True)
    parser.add_argument("--diff", required=True)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()

    # 初始化 MCP 客户端
    client = Client()

    # 构建上下文
    context = {
        "files": args.files.split(),
        "diff": args.diff,
        "pr_number": args.pr
    }

    # 调用模型
    response = client.query(
        model="code-review-llm",
        context=context,
        prompt="请检查代码风格、潜在 bug，并给出改进建议"
    )

    # 将结果写入 GitHub 评论
    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr = repo.get_pull(int(args.pr))
    pr.create_issue_comment(f"🤖 MCP Review:\n\n{response}")

if __name__ == "__main__":
    main()
