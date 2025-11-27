# CodeReview
software engineer project

This is a project for code review.
We use Langgraph to build a workflow for automatically executing detail review.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
python scripts/mcp_review.py --files <files> --diff-file <diff> --pr <pr_number>
```