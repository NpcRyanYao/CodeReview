"""
Diff 获取：在 workflow 里实现了 git diff base...head，能收集修改的代码。
风格检查：你提到 tree-sitter +规则，这部分如果已经接入，就能做 fast check。
文档要求：目前还需要明确如何把需求文档输入到 pipeline（例如作为额外上下文文件）。
相关函数/方法：向量数据库检索还没在 workflow 里体现，但你已经规划了。
LSP 审评意见：如果你能调用 LSP 或静态分析工具（如 pylsp、eslint），就能补充安全/逻辑检查。
结果反馈到 GitHub：你已经实现了 pr.create_issue_comment(...)，结果能自动出现在 PR 页面。
"""
import asyncio
import sys
import os

# 把项目根目录加入 sys.path (必须在导入之前)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 把 scripts 目录加入 sys.path 以便导入 code_review_core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_review_core import fine_code_review
import argparse
import re
import json
import subprocess
from github import Github, Auth

from client import Client

def parse_diff_by_file(diff_text: str):
    """
    从统一的 diff 文本中按文件拆分，返回 {file_path: diff_body}
    兼容新增/删除文件，若没有 @@ hunk，就用整块内容降级。
    """
    files_to_diff = {}
    blocks = re.split(r'(?=^diff --git)', diff_text, flags=re.MULTILINE)
    for block in blocks:
        if not block.strip().startswith("diff --git"):
            continue

        m = re.search(r'^\+\+\+ b/(.+)$', block, flags=re.MULTILINE)
        if not m:
            m2 = re.search(r'^--- a/(.+)$', block, flags=re.MULTILINE)
            file_path = m2.group(1).strip() if m2 else None
        else:
            file_path = m.group(1).strip()

        if not file_path:
            continue

        hunk = re.search(r'@@.*\n([\s\S]*)', block)
        diff_body = (hunk.group(1).strip() if hunk else block.strip())
        files_to_diff[file_path] = diff_body

    return files_to_diff


def get_commit_message(commit_hash=None):
    """获取指定 commit 的 message，默认取最后一次"""
    try:
        cmd = ["git", "log", "-1", "--pretty=%B"]
        if commit_hash:
            cmd.append(commit_hash)
        return subprocess.check_output(cmd, text=True).strip()
    except Exception:
        return ""


def get_commits_in_range(base_sha, head_sha):
    """获取 PR 范围内所有 commit 信息"""
    commits = []
    try:
        output = subprocess.check_output(
            ["git", "log", "--pretty=format:%H", f"{base_sha}..{head_sha}"],
            text=True
        )
        hashes = output.strip().splitlines()
        for h in hashes:
            commits.append({
                "hash": h,
                "message": get_commit_message(h)
            })
    except Exception:
        pass
    return commits


def extract_first_added_line_position(diff_body: str):
    """解析 diff hunk，返回第一个新增行的 position，默认 1"""
    m = re.search(r'@@ -\d+(?:,\d+)? \+(\d+)', diff_body)
    if m:
        return int(m.group(1))
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--req", required=False)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--base-sha", required=False)
    args = parser.parse_args()

    graph_result = asyncio.run(fine_code_review())

    with open(args.diff_file, "r", encoding="utf-8") as f:
        full_diff = f.read()

    requirements = graph_result["document"]

    client = Client(
        api_base_url="https://api.deepseek.com",
        api_key="sk-413bc9536ec04094a4a05e0e1d17bc3b",
        model_name="deepseek-chat",
        system_prompt="You are a code review expert, and now we need you to provide the review content based on the context dictionary. Please provide the overall review first. You need to use English."
    )
    changed_files = args.files.split()
    diff_map = parse_diff_by_file(full_diff)

    # 收集 commit 信息（支持多个）
    commits = []
    if args.base_sha:
        commits = get_commits_in_range(args.base_sha, os.getenv(
            "GITHUB_SHA", ""))

    context = {
        "files": changed_files,
        "diff": full_diff,
        "diffs_by_file": diff_map,
        "requirements": requirements,
        "pr_number": args.pr,
        "root_path": os.path.abspath(os.getcwd()),
        "commits": commits if commits else [{
            "hash": os.getenv("GITHUB_SHA", ""),
            "message": get_commit_message()
        }],
        "lsp_diagnostics": graph_result["diagnostics"],
        "related_code": graph_result["semantic_analysis"]
    }

    overall = client.send(context, format_type="pretty")

    gh = Github(auth=Auth.Token(os.getenv("GITHUB_TOKEN")))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr = repo.get_pull(int(args.pr))

    pr.create_issue_comment(f"🤖 MCP Review(Overall):\n\n{overall}")

    comments = []
    client.send("Now conduct a specific review of the documents I have provided")
    for file in changed_files:
        file_diff = diff_map.get(file, "")
        file_ctx = {
            "file": file,
            "diff": file_diff,
            "requirements": requirements,
            "pr_number": args.pr,
        }

        position = extract_first_added_line_position(file_diff)
        file_review = client.send(file_ctx)
        comments.append({
            "path": file,
            "position": position,
            "body": f"🤖 Document review：{file}\n\n{file_review}"
        })

    if comments:
        pr.create_review(
            body="🤖 Accurate evaluation results of documents",
            event="COMMENT",
            comments=comments
        )
    for comment in comments:
        print(comment)

    print("✅ Written back to overall review and sub file evaluation")


if __name__ == "__main__":
    main()
