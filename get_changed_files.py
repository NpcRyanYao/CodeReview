import subprocess
import re
import json


def run_git_command(cmd, cwd=None, check=True, encoding='utf-8'):
    """
    Run git command and return stdout as a string.
    Uses errors='replace' to avoid UnicodeDecodeError on Windows.
    If the command fails and check=True, raise CalledProcessError.
    If it fails and check=False, return stderr or empty string.
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors='replace',
            check=check
        )
    except subprocess.CalledProcessError as e:
        # 如果你希望在出错时向上抛出，删掉下面两行的返回并 raise e
        # 这里返回 stderr（已替换不可解码字节）以便上层判断处理
        return (e.stderr or "").strip()
    except Exception:
        # 其它异常继续抛出，方便调试
        raise
    return (result.stdout or "").strip()


def git_show_output(output):
    """ get the output --> dic"""
    lines = output.splitlines()

    info = {
        "hash": "",
        "message": "",
    }

    for i, line in enumerate(lines):
        if line.startswith("commit "):
            info["hash"] = line.split()[1]
        elif line.startswith("Author:"):
            match = re.match(r"Author:\s*(.*?)\s*<(.*?)>", line)
            if match:
                continue
        elif line.startswith("Date:"):
            continue
        elif line.strip() == "":
            # get commit message
            if i + 1 < len(lines) and lines[i + 1].startswith("    "):
                message_lines = []
                j = i + 1
                while j < len(lines) and lines[j].startswith("    "):
                    message_lines.append(lines[j].strip())
                    j += 1
                info["message"] = "\n".join(message_lines)
                break

    # get diff blocks
    diff_blocks = re.split(r'(?=^diff --git)', output, flags=re.MULTILINE)
    diff_dict = {}
    for block in diff_blocks:
        if not block.strip().startswith("diff --git"):
            continue
        match = re.search(r'b/([^\s]+)', block)
        if not match:
            continue
        file_path = match.group(1)

        # get real diff (从第一个 @@ 匹配后取其余)
        diff_content_match = re.search(r'@@.*\n([\s\S]*)', block)
        if diff_content_match:
            diff_content = diff_content_match.group(1).strip()
        else:
            # 如果没有 @@，可能是新文件/删除/二进制等，用整块内容作为降级方案
            # 也可改为 "" 或特定标识
            diff_content = block.strip()

        diff_dict[file_path] = diff_content
    # 将 diff 字典放到 info 的一个字段里，避免与其他键冲突
    info["diffs"] = diff_dict
    return info


def get_last_commit_info():
    """get the last commit detail"""
    try:
        commit_hash = run_git_command([
            "git", "log",
            "-1", "--pretty=format:%H"
        ])
        if not commit_hash:
            print("❌ git log 返回空，可能仓库为空或命令执行失败")
            return None

        commit_details = run_git_command(["git", "show", commit_hash])
        if not commit_details:
            print("❌ git show 返回空，可能包含二进制内容或命令失败")
            return None

        commit_info = git_show_output(commit_details)
        return commit_info

    except subprocess.CalledProcessError as e:
        print("❌ execute Git fail:", e)
        return None


if __name__ == "__main__":
    info = get_last_commit_info()
    if not info:
        print("No commit info available.")
    else:
        # 美化输出
        print(json.dumps(info, indent=2, ensure_ascii=False))
