# 代码审查工具

一个基于 AI 的智能代码审查工具，集成了 LSP 诊断、语义分析和大语言模型评审，可自动化完成代码审查并将结果反馈到 GitHub PR。

[English](README.md) | 简体中文

## 功能特性

### 核心功能

- **Git Diff 分析**: 自动获取代码变更，支持单次 commit 和多次 commit 的 diff 分析
- **快速风格检查**: 基于 tree-sitter 的代码风格检查（缩进、命名规范等）
- **LSP 诊断**: 集成 Java Language Server，提供语法错误、类型检查等静态分析
- **语义分析**: 使用 CodeBERT 向量化代码，检索相似函数和相关代码片段
- **LLM 智能评审**: 基于 DeepSeek API 的深度代码审查，结合需求文档和上下文
- **GitHub 集成**: 自动将审查结果以评论形式发布到 GitHub PR

### 工作流程

项目使用 LangGraph 构建了一个多阶段的审查工作流：

```
开始
  ├─> 读取需求文档
  ├─> LSP 诊断分析
  └─> 向量数据库检索
       ↓
  LLM 综合评审
       ↓
  发布到 GitHub
```

## 项目结构

```
.
├── scripts/
│   ├── client.py                    # DeepSeek API 客户端
│   ├── mcp_review.py               # GitHub PR 审查主入口
│   ├── .env                        # API 密钥配置
│   └── code_review_core/
│       ├── diffGet.py              # Git diff 解析工具
│       ├── fast_check.py           # 快速风格检查
│       ├── fine_review.py          # 精细审查入口
│       └── agent/
│           ├── core.py             # LangGraph 工作流引擎
│           ├── state.py            # 状态管理
│           ├── lsp/                # LSP 诊断模块
│           │   ├── analyzer.py
│           │   ├── lsp_client.py
│           │   └── server_manager.py
│           └── semantic_analyzer/  # 语义分析模块
│               ├── analyzer.py
│               ├── code_parser.py
│               ├── vector_manager.py
│               └── data_models.py
├── src/                            # 示例 Java 项目
├── document/                       # 需求文档目录
└── requirements.txt
```

## 安装

### 环境要求

- Python 3.8+
- Java 11+ (用于 LSP 服务器)
- Git

### 安装依赖

项目提供了两个依赖文件：

**本地开发环境**（包含完整开发工具）：
```bash
pip install -r scripts/requirements.txt
```

**GitHub Actions / CI 环境**（精简版，仅运行时依赖）：
```bash
pip install -r requirements.txt
```

**使用 conda（推荐本地开发）**：
```bash
conda create -n code-review python=3.9
conda activate code-review
pip install -r requirements.txt
```

### 配置 API 密钥

在 `scripts/.env` 文件中配置你的 DeepSeek API 密钥：

```env
DEEPSEEK_API_KEY=your_api_key_here
```

## 使用方法

### 1. 本地代码审查

对最近一次 commit 进行审查：

```bash
cd scripts
python -m code_review_core.fine_review
```

### 2. GitHub PR 审查

GitHub Actions 会自动触发审查（已配置 workflow）。

手动运行命令：

```bash
python scripts/mcp_review.py \
  --files "src/File1.java src/File2.java" \
  --diff-file diff.txt \
  --pr 123 \
  --base-sha abc123
```

### 3. 快速风格检查

```bash
python scripts/code_review_core/fast_check.py <项目根目录>
```

### 4. LSP 诊断

```bash
python scripts/code_review_core/agent/lsp/analyzer.py <项目路径> [文件1] [文件2]
```

## 配置说明

### 语义分析配置

在 `semantic_analyzer/analyzer.py` 中可以调整：

- `rebuild_threshold`: 触发全量重建的变更文件比例（默认 0.3）
- `min_files_for_rebuild`: 最小文件数阈值（默认 10）
- `model_name`: 使用的代码向量化模型（默认 "microsoft/codebert-base"）

### LLM 配置

在 `client.py` 中可以调整：

- `model_name`: 使用的模型（默认 "deepseek-chat"）
- `temperature`: 生成温度（默认 0.7）
- `max_tokens`: 最大生成长度（默认 2048）

## 技术栈

- **LangGraph**: 工作流编排
- **LangChain**: LLM 集成框架
- **ChromaDB**: 向量数据库
- **Tree-sitter**: 代码语法解析
- **LSP (Language Server Protocol)**: 静态代码分析
- **Transformers**: CodeBERT 模型
- **PyGithub**: GitHub API 集成

## 架构设计

### 工作流引擎

使用 LangGraph 构建的状态机工作流，支持：

- 并行执行多个分析任务
- 条件分支和循环
- 状态持久化和恢复
- 错误处理和重试机制

### 语义分析

- **增量更新**: 仅分析变更的代码，提高效率
- **智能重建**: 当变更超过阈值时自动触发全量重建
- **向量检索**: 基于 CodeBERT 的语义相似度搜索

### LSP 集成

- 支持 Java Language Server
- 提供实时诊断信息
- 可扩展到其他语言服务器

## 开发计划

- [ ] 支持更多编程语言（目前主要支持 Java 和 Python）
- [ ] 增加代码安全漏洞检测
- [ ] 支持自定义审查规则
- [ ] 添加 Web UI 界面
- [ ] 性能优化和缓存机制
- [ ] 支持本地 LLM 模型

## 常见问题

### Q: 如何更换 LLM 提供商？

A: 修改 `client.py` 中的 `api_base_url` 和相关配置即可，支持任何兼容 OpenAI API 格式的服务。

### Q: 向量数据库存储在哪里？

A: ChromaDB 默认存储在项目根目录的 `chroma_db` 文件夹中。

### Q: 如何添加自定义检查规则？

A: 在 `fast_check.py` 中添加新的检查函数，并在 `run_checks` 方法中调用。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

### 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

如有问题或建议，欢迎通过 Issue 联系我们。
