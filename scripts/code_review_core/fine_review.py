import asyncio
import os
import sys

# Handle imports for both module import and direct script execution
try:
    # Try relative imports first (when imported as module)
    from .agent import AgentCore
    from .diffGet import get_all_commit_info, run_git_command, get_last_commit_info
except ImportError:
    # If relative imports fail, add paths and use absolute imports (when run as script)
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, scripts_dir)
    from code_review_core.agent import AgentCore
    from code_review_core.diffGet import get_all_commit_info, run_git_command, get_last_commit_info


def get_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    root_indicators = ['src', "scripts"]

    while current_dir != os.path.dirname(current_dir):
        for indicator in root_indicators:
            if os.path.exists(os.path.join(current_dir, indicator)):
                return current_dir
        current_dir = os.path.dirname(current_dir)

    return current_dir

async def fine_code_review():
    project_root = get_project_root()

    # get diff info
    info = get_last_commit_info(project_root)

    agent = AgentCore()
    file_path = []
    for key, value in info["diff"].items():
        file_path.append(key)

    commit_details = get_all_commit_info(project_root)
    result = await agent.review_code(git_diff=commit_details, project_path=project_root, file_paths=file_path)
    return result

if __name__ == "__main__":
    asyncio.run(fine_code_review())