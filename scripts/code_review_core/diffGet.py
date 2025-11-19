import os
import subprocess #use shell
import re
import json
import sys


def run_git_command(cmd, cwd):
    """excute git and return result"""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd, encoding="utf-8")
    return result.stdout.strip()

def git_show_output(output):
    """ get the output --> dic"""
    lines = output.splitlines()

    info = {
        "hash": "",
        "message": "",
        "diff":{}
    }

    for i, line in enumerate(lines):
        if line.startswith("commit "):
            info["hash"] = line.split()[1]
        elif line.startswith("Author:"):
            match = re.match(r"Author:\s*(.*?)\s*<(.*?)>", line)
            if match:
                # info["author"] = match.group(1).strip()
                # info["email"] = match.group(2).strip()
                continue
        elif line.startswith("Date:"):
            # info["date"] = line.replace("Date:", "").strip()
            continue
        elif line.strip() == "":
            # get commit message
            if i + 1 < len(lines) and lines[i+1].startswith("    "):
                message_lines = []
                j = i + 1
                while j < len(lines) and lines[j].startswith("    "):
                    message_lines.append(lines[j].strip())
                    j += 1
                info["message"] = "\n".join(message_lines)
                break

    # get diff
    diff_blocks = re.split(r'(?=^diff --git)', output, flags=re.MULTILINE)
    diff_dict = {}
    for block in diff_blocks:
        if not block.strip().startswith("diff --git"):
            continue
        match = re.search(r'b/([^\s]+)', block)
        if not match:
            continue
        file_path = match.group(1)

        # get real diff
        diff_content_match = re.search(r'@@.*\n([\s\S]*)', block)
        if diff_content_match:
            diff_content = diff_content_match.group(1).strip()
        else:
            diff_content = "the code didn't make any change"

        diff_dict[file_path] = diff_content
    info["diff"] = diff_dict

    #         # get real diff[all diffs in a dic as a value for the key "diff" in info]
    #     diff_content_match = re.search(r'@@.*\n([\s\S]*)', block)
    #     if diff_content_match:
    #         diff_content = diff_content_match.group(1).strip()
    #     else:
    #         diff_content = "the code didn't make any change"

    #     diff_dict[file_path] = diff_content
    # info['diff'] = diff_content
    return info

def get_last_commit_info(project_path):
    """get the last commit detail"""
    try:
        commit_hash = run_git_command(["git", "log", "-1", "--pretty=format:%H"], project_path)

        commit_details = run_git_command(["git", "show", commit_hash], project_path)
        commit_info = git_show_output(commit_details)
        return commit_info

    except subprocess.CalledProcessError as e:
        print("❌ excute Git fail:", e)
        return None

def get_all_commit_info(project_path):
    """get the all commit detail"""
    try:
        commit_hashes = run_git_command(["git", "log", "--pretty=format:%H"], project_path)
        commit_hashes = [hash.strip() for hash in commit_hashes.split('\n') if hash.strip()]

        all_diffs = []
        for commit_hash in commit_hashes:
            if commit_hash:
                # 获取单个commit的diff信息
                commit_diff = run_git_command(["git", "show", commit_hash, "--pretty=format:", "-p"], project_path)
                all_diffs.append(commit_diff)

        all_diffs_combined = "\n\n".join(all_diffs)

        return all_diffs_combined

    except subprocess.CalledProcessError as e:
        print("❌ excute Git fail:", e)
        return None

def main():
    project_root = sys.argv[1]

    info = get_last_commit_info(project_root)
    for key, value in info.items():
        print(f"{key}:\n{value}")

if __name__ == "__main__":
    main()