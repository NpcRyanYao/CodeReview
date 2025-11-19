import os

from scripts.code_review_core.diffGet import get_all_commit_info, run_git_command


def get_project_root():
    """获取项目根目录路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))

    root_indicators = ['.git']

    while current_dir != os.path.dirname(current_dir):
        for indicator in root_indicators:
            if os.path.exists(os.path.join(current_dir, indicator)):
                return current_dir
        current_dir = os.path.dirname(current_dir)

    return current_dir

def main():
    project_root = get_project_root()
    # commit_hashes = run_git_command(["git", "log", "--pretty=format:%H"], project_root)
    # print(type(commit_hashes))
    commit_details = get_all_commit_info(project_root)
    print(commit_details)

if __name__ == "__main__":
    main()