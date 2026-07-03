# AutoIdea

AutoIdea retrieves new papers from arXiv, bioRxiv, and medRxiv, ranks them against your existing reading history, and turns the top results into actionable daily output.

This repository is a modified fork of [`TideDra/zotero-arxiv-daily`](https://github.com/TideDra/zotero-arxiv-daily).

For each selected paper, the workflow can generate:

- A one-sentence TLDR
- A structured outline: `problem / method / finding / limitation`
- Practical ideas: research directions, engineering improvements, workflow ideas, and experiment suggestions
- A daily cross-paper summary: `Today's Top Directions`

## Config Links

- [config/default.yaml](https://github.com/wangerforcs/AutoIdea/blob/main/config/default.yaml)
- [config/base.yaml](https://github.com/wangerforcs/AutoIdea/blob/main/config/base.yaml)
- [config/custom.yaml](https://github.com/wangerforcs/AutoIdea/blob/main/config/custom.yaml)

## Notes

- `default.yaml` loads `base + custom`.
- The public project name is `AutoIdea`.
- For compatibility, the current config keys and Python package names still use `zotero` / `zotero_arxiv_daily`.

## Features

- Daily paper retrieval from arXiv, bioRxiv, and medRxiv
- Relevance ranking against your Zotero library
- Per-paper TLDR generation
- Configurable TLDR length: one sentence, short summary, or detailed summary
- Per-paper structured paper decomposition
- Per-paper idea generation
- Daily high-level idea selection with explicit innovation and evidence
- Email delivery of the final digest

## Configuration

Full configuration schema:

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
  tldr_style: short_summary

idea:
  enabled: true
  mode: balanced
  max_num: 3
  daily_summary_num: 3
  context_paper_num: 5
  show_per_paper: false
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

Example `custom.yaml`:

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
  tldr_style: short_summary

idea:
  enabled: true
  mode: research
  max_num: 3
  daily_summary_num: 3
  context_paper_num: 5
  focus: "Prioritize ideas that improve ongoing research, workflow quality, or fast validation experiments."

source:
  arxiv:
    category: ["cs.AI","cs.CV","cs.LG","cs.CL"]
    include_cross_list: false

executor:
  debug: ${oc.env:DEBUG,null}
  source: ['arxiv']
```

## Environment Variables

Minimum environment variables:

```bash
export ZOTERO_ID=xxxx
export ZOTERO_KEY=xxxx
export SENDER=you@example.com
export RECEIVER=you@example.com
export SENDER_PASSWORD=xxxx
export OPENAI_API_KEY=sk-xxx
export OPENAI_API_BASE=https://api.openai.com/v1
```

You can also place these values in a local `.env` file. The application loads it automatically at startup.

## Local Run

Run from the repository root:

```bash
uv run python -m zotero_arxiv_daily.main
```

Example with temporary Hydra overrides:

```bash
uv run python -m zotero_arxiv_daily.main \
  executor.debug=true \
  executor.source=[arxiv] \
  idea.max_num=5 \
  llm.language=Chinese
```

## Pipeline

The execution flow is:

1. Load your historical corpus from Zotero.
2. Retrieve newly published papers from the selected sources.
3. Rank candidates with the configured embedding reranker.
4. Generate a TLDR for each selected paper.
5. Extract a structured outline for each paper.
6. Generate per-paper ideas using the paper content and recent corpus context.
7. Generate a daily cross-paper selection of the most feasible ideas, each explained in plain language and accompanied by innovation, feasibility reasoning, evidence from papers, and a first validation step.
8. Send the final digest by email.

`idea.mode` controls the default orientation of the output:

- `research`: prioritize hypotheses, experiments, evaluations, benchmarks, and publishable research directions
- `balanced`: mix research and practical implementation ideas
- `engineering`: prioritize tools, automation, infrastructure, and implementation plans

## Email Output

Each email contains:

- A top summary section with the most actionable directions for the day
- Each selected idea includes:
  - the idea itself, written as a plain-language short explanation
  - why it is innovative
  - why it is feasible
  - evidence from specific papers
  - the first practical validation step
- A per-paper section with:
  - Title
  - Authors
  - Affiliations
  - Relevance score
  - TLDR
  - Ideas
  - PDF link

## Testing

Run the main local test set with:

```bash
uv run pytest tests/test_protocol.py tests/test_construct_email.py tests/test_executor.py tests/test_main.py
```

## License

This repository is based on and modified from [`TideDra/zotero-arxiv-daily`](https://github.com/TideDra/zotero-arxiv-daily).
The modified work is distributed under the GNU Affero General Public License v3.0 (AGPL-3.0).
Please keep the original license terms when redistributing or deploying modified versions.
