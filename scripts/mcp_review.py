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
import json


def parse_diff_file(diff_file_path):
    """按文件拆分 diff 内容，返回 {file_path: diff_content}"""
    if not os.path.exists(diff_file_path):
        return {}
    with open(diff_file_path, "r", encoding="utf-8") as f:
        diff_content = f.read()

    diff_blocks = diff_content.split("diff --git")
    diff_dict = {}
    for block in diff_blocks:
        if not block.strip():
            continue
        # 提取文件路径
        lines = block.splitlines()
        file_path = None
        for line in lines:
            if line.startswith("--- a/") or line.startswith("+++ b/"):
                if line.startswith("+++ b/"):
                    file_path = line.replace("+++ b/", "").strip()
                    break
        if not file_path:
            continue
        # 提取 diff 内容（去掉头部）
        diff_body = "\n".join(lines[1:])
        diff_dict[file_path] = diff_body
    return diff_dict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--req", required=False)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()

    # 读取需求文档
    requirements = None
    if args.req and os.path.exists(args.req):
        with open(args.req, "r", encoding="utf-8") as f:
            requirements = f.read()

    # 构建字典结构
    commit_info_dict = {
        "root_path": os.path.abspath(os.getcwd()),
        "commit": {
            "hash": os.getenv("GITHUB_SHA", ""),   # CI 环境里有当前 commit SHA
            "message": os.getenv("COMMIT_MESSAGE", "")  # 可以在 workflow 里提前写入
        },
        "diffs": parse_diff_file(args.diff_file),
        "files": args.files.split(),
        "requirements": requirements,
        "pr_number": args.pr
    }

    # 打印 JSON，方便在 CI 日志里查看
    print(json.dumps(commit_info_dict, indent=2, ensure_ascii=False))

    # 调用 LLM 做评审
    client = Client()
    response = client.query(
        model="code-review-llm",
        context=commit_info_dict,
        prompt="请检查代码风格、潜在 bug、逻辑问题，并比对需求文档，给出改进建议"
    )

    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr = repo.get_pull(int(args.pr))

    pr.create_issue_comment(f"🤖 MCP Review:\n\n{response}")


if __name__ == "__main__":
    main()
