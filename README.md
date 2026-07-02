原始参考仓库：[`TideDra/zotero-arxiv-daily`](https://github.com/TideDra/zotero-arxiv-daily)

# AutoIdea

这个项目会根据你的文献库偏好，从 arXiv / bioRxiv / medRxiv 拉取新论文，按与你近期兴趣的相关性排序，并生成：

- 每篇论文的 TLDR
- 每篇论文的结构化摘要：`problem / method / finding / limitation`
- 每篇论文的 ideas：研究方向、工程改进、workflow 改进、实验建议
- 当天论文的汇总方向：`Today's Top Directions`

## 配置

配置入口：

- [config/default.yaml](https://github.com/wangerforcs/AutoIdea/blob/main/config/default.yaml)
- [config/base.yaml](https://github.com/wangerforcs/AutoIdea/blob/main/config/base.yaml)
- [config/custom.yaml](https://github.com/wangerforcs/AutoIdea/blob/main/config/custom.yaml)

`default.yaml` 会加载 `base + custom`。

说明：当前配置键名和 Python 包名为了兼容现有代码仍保留 `zotero_*` / `zotero:`，但对外项目名称统一为 `AutoIdea`。

完整配置如下：

```yaml
zotero:
  user_id: ??? # User ID of your Zotero account.
  api_key: ??? # A Zotero API key with read access.
  include_path: null # Example: ["2026/survey/**","2026/reading-group/**"]
  ignore_path: null # Example: ["archive/**","2026/ignore/**"]

source:
  arxiv:
    category: null # Example: ["cs.AI","cs.CV","cs.LG","cs.CL"]
    include_cross_list: false
  biorxiv:
    category: null
  medrxiv:
    category: null

email:
  sender: ???
  receiver: ???
  smtp_server: ???
  smtp_port: ???
  sender_password: ???

llm:
  api:
    key: ???
    base_url: ???
  generation_kwargs:
    max_tokens: 16384
    model: ???
  language: English

idea:
  enabled: true
  max_num: 3
  daily_summary_num: 3
  context_paper_num: 5
  focus: null # Example: "Focus on ideas that can improve my workflow and current research."

reranker:
  local:
    model: jinaai/jina-embeddings-v5-text-nano-retrieval
    encode_kwargs:
      task: retrieval
      prompt_name: document
  api:
    key: null
    base_url: null
    model: null
    batch_size: null

executor:
  debug: false
  send_empty: false
  max_paper_num: 100
  source: ???
  reranker: local
```

一个可直接改的 `custom` 示例：

```yaml
zotero:
  user_id: ${oc.env:ZOTERO_ID}
  api_key: ${oc.env:ZOTERO_KEY}
  include_path: null

email:
  sender: ${oc.env:SENDER}
  receiver: ${oc.env:RECEIVER}
  smtp_server: smtp.qq.com
  smtp_port: 465
  sender_password: ${oc.env:SENDER_PASSWORD}

llm:
  api:
    key: ${oc.env:OPENAI_API_KEY}
    base_url: ${oc.env:OPENAI_API_BASE}
  generation_kwargs:
    model: gpt-4o-mini
  language: Chinese

idea:
  enabled: true
  max_num: 3
  daily_summary_num: 3
  context_paper_num: 5
  focus: "优先生成能启发后续研究、改进当前工作流、或能快速验证的新实验想法。"

source:
  arxiv:
    category: ["cs.AI","cs.CV","cs.LG","cs.CL"]
    include_cross_list: false

executor:
  debug: ${oc.env:DEBUG,null}
  source: ['arxiv']
```

## 环境变量

如果你沿用 GitHub Actions 的方式，至少需要这些变量：

```bash
export ZOTERO_ID=xxxx
export ZOTERO_KEY=xxxx
export SENDER=you@example.com
export RECEIVER=you@example.com
export SENDER_PASSWORD=xxxx
export OPENAI_API_KEY=sk-xxx
export OPENAI_API_BASE=https://api.openai.com/v1
```

也可以在项目根目录放 `.env`，程序启动时会自动加载。

## 本地运行

安装 `uv` 后，在项目根目录执行：

```bash
uv run python -m zotero_arxiv_daily.main
```

临时覆盖配置可以直接用 Hydra override：

```bash
uv run python -m zotero_arxiv_daily.main \
  executor.debug=true \
  executor.source=[arxiv] \
  idea.max_num=5 \
  llm.language=Chinese
```

## Auto Idea 流程

执行链路在 [src/zotero_arxiv_daily/executor.py](https://github.com/wangerforcs/AutoIdea/blob/main/src/zotero_arxiv_daily/executor.py)：

1. 从你的历史文献库拉取语料
2. 从论文源拉取当天新论文
3. 用 embedding reranker 按相关性排序
4. 对每篇论文生成 `TLDR`
5. 对每篇论文抽取结构化要点：`problem / method / finding / limitation`
6. 基于论文内容和近期语料上下文生成 ideas
7. 汇总当天所有论文，生成 `Today's Top Directions`
8. 发送邮件

单篇论文的 idea 逻辑在 [src/zotero_arxiv_daily/protocol.py](https://github.com/wangerforcs/AutoIdea/blob/main/src/zotero_arxiv_daily/protocol.py)。

## 输出内容

邮件里现在包含两层内容：

- 顶部汇总：当天最值得做的 3 个方向
- 逐篇论文块：
  - 标题
  - 作者
  - 机构
  - relevance score
  - TLDR
  - ideas
  - PDF 链接

## 测试

本地验证命令：

```bash
uv run pytest tests/test_protocol.py tests/test_construct_email.py tests/test_executor.py tests/test_main.py
```
