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

    # 按 diff --git 分块
    blocks = re.split(r'(?=^diff --git)', diff_text, flags=re.MULTILINE)
    for block in blocks:
        if not block.strip().startswith("diff --git"):
            continue

        # 解析文件路径（以 b/ 为准）
        m = re.search(r'^\+\+\+ b/(.+)$', block, flags=re.MULTILINE)
        if not m:
            # 有些场景是 /dev/null（删除文件），尝试从 --- a/ 提取
            m2 = re.search(r'^--- a/(.+)$', block, flags=re.MULTILINE)
            file_path = m2.group(1).strip() if m2 else None
        else:
            file_path = m.group(1).strip()

        if not file_path:
            continue

        # 提取真正的 diff 内容（从第一个 @@ 开始）
        hunk = re.search(r'@@.*\n([\s\S]*)', block)
        diff_body = (hunk.group(1).strip() if hunk else block.strip())

        files_to_diff[file_path] = diff_body

    return files_to_diff


def get_commit_message():
    """获取最后一次提交的 message"""
    try:
        return subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"],
            text=True
        ).strip()
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--req", required=False)
    parser.add_argument("--pr", required=True)
    args = parser.parse_args()

    # 读取 diff 内容
    with open(args.diff_file, "r", encoding="utf-8") as f:
        full_diff = f.read()

    # 读取需求文档
    requirements = None
    if args.req and os.path.exists(args.req):
        with open(args.req, "r", encoding="utf-8") as f:
            requirements = f.read()

    client = Client()

    changed_files = args.files.split()
    diff_map = parse_diff_by_file(full_diff)

    # 构建整体上下文
    context = {
        "files": changed_files,                # 改动的文件路径列表
        "diff": full_diff,                     # 整个 PR 的完整 diff 内容
        "diffs_by_file": diff_map,             # 按文件拆分后的 diff
        "requirements": requirements,          # 需求文档内容
        "pr_number": args.pr,                  # 当前 PR 编号
        "root_path": os.path.abspath(os.getcwd()),  # 项目根路径
        "commit": {                            # 当前提交信息
            "hash": os.getenv("GITHUB_SHA", ""),
            "message": get_commit_message()
        }
    }

    # 打印字典结构到日志
    print("📦 Context 字典结构:")
    print(json.dumps(context, indent=2, ensure_ascii=False))

    # 整体评审结果
    overall = client.query(
        model="code-review-llm",
        context=context,
        prompt="请检查代码风格、潜在 bug、逻辑问题，并比对需求文档，给出改进建议。必要时引用具体 diff 片段。"
    )

    gh = Github(auth=Auth.Token(os.getenv("GITHUB_TOKEN")))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr = repo.get_pull(int(args.pr))

    # 1️⃣ 保留 Conversation 评论
    pr.create_issue_comment(f"🤖 MCP Review（整体）:\n\n{overall}")

    # 2️⃣ 分文件精确评审
    comments = []
    for file in changed_files:
        file_diff = diff_map.get(file, "")
        file_ctx = {
            "files": [file],
            "file": file,
            "diff": file_diff,
            "requirements": requirements,
            "pr_number": args.pr,
        }

        file_review = client.query(
            model="code-review-llm",
            context=file_ctx,
            prompt=f"请基于该文件的 diff 片段进行精确评审，指出问题和改进建议：{file}"
        )

        comments.append({
            "path": file,
            "position": 1,  # 简单挂在文件开头
            "body": f"🤖 文件评审：{file}\n\n{file_review}"
        })

    if comments:
        pr.create_review(
            body="🤖 分文件精确评审结果",
            event="COMMENT",
            comments=comments
        )

    print("✅ 已写回整体评论与分文件评审")


if __name__ == "__main__":
    main()
