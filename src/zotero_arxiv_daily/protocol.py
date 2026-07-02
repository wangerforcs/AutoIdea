from dataclasses import dataclass
from typing import Optional, TypeVar
from datetime import datetime
import re
import tiktoken
from openai import OpenAI
from loguru import logger
import json
RawPaperItem = TypeVar('RawPaperItem')


def _extract_json_payload(content: str):
    content = content.strip()
    if content.startswith("{"):
        return json.loads(content)
    if content.startswith("["):
        return json.loads(content)

    object_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if object_match:
        return json.loads(object_match.group(0))

    list_match = re.search(r"\[.*\]", content, flags=re.DOTALL)
    if list_match:
        return json.loads(list_match.group(0))

    raise ValueError("No JSON payload found in LLM response")

@dataclass
class Paper:
    source: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None
    tldr: Optional[str] = None
    idea_outline: Optional[dict[str, str]] = None
    ideas: Optional[list[str]] = None
    affiliations: Optional[list[str]] = None
    score: Optional[float] = None

    def _generate_tldr_with_llm(self, openai_client:OpenAI,llm_params:dict) -> str:
        lang = llm_params.get('language', 'English')
        prompt = f"Given the following information of a paper, generate a one-sentence TLDR summary in {lang}:\n\n"
        if self.title:
            prompt += f"Title:\n {self.title}\n\n"

        if self.abstract:
            prompt += f"Abstract: {self.abstract}\n\n"

        if self.full_text:
            prompt += f"Preview of main content:\n {self.full_text}\n\n"

        if not self.full_text and not self.abstract:
            logger.warning(f"Neither full text nor abstract is provided for {self.url}")
            return "Failed to generate TLDR. Neither full text nor abstract is provided"
        
        # use gpt-4o tokenizer for estimation
        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        prompt_tokens = prompt_tokens[:4000]  # truncate to 4000 tokens
        prompt = enc.decode(prompt_tokens)
        
        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"You are an assistant who perfectly summarizes scientific paper, and gives the core idea of the paper to the user. Your answer should be in {lang}.",
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get('generation_kwargs', {})
        )
        tldr = response.choices[0].message.content
        return tldr
    
    def generate_tldr(self, openai_client:OpenAI,llm_params:dict) -> str:
        try:
            tldr = self._generate_tldr_with_llm(openai_client,llm_params)
            self.tldr = tldr
            return tldr
        except Exception as e:
            logger.warning(f"Failed to generate tldr of {self.url}: {e}")
            tldr = self.abstract
            self.tldr = tldr
            return tldr

    def _generate_idea_outline_with_llm(self, openai_client: OpenAI, llm_params: dict) -> dict[str, str]:
        if not self.abstract and not self.full_text:
            logger.warning(f"Neither full text nor abstract is provided for {self.url}")
            return {}

        lang = llm_params.get("language", "English")
        prompt = (
            f"Extract the key points of this paper in {lang}. "
            "Return JSON only with keys: problem, method, finding, limitation. "
            "Each value should be one concise sentence.\n\n"
        )
        if self.title:
            prompt += f"Title:\n{self.title}\n\n"
        if self.tldr:
            prompt += f"TLDR:\n{self.tldr}\n\n"
        if self.abstract:
            prompt += f"Abstract:\n{self.abstract}\n\n"
        if self.full_text:
            prompt += f"Content preview:\n{self.full_text}\n\n"

        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt = enc.decode(enc.encode(prompt)[:4500])
        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract scientific papers into concise structured notes. "
                        "Return JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get("generation_kwargs", {})
        )
        outline = _extract_json_payload(response.choices[0].message.content)
        if not isinstance(outline, dict):
            raise ValueError("Idea outline response is not an object")
        normalized = {}
        for key in ("problem", "method", "finding", "limitation"):
            value = outline.get(key, "")
            normalized[key] = str(value).strip() if value is not None else ""
        return normalized

    def generate_idea_outline(self, openai_client: OpenAI, llm_params: dict) -> dict[str, str]:
        try:
            outline = self._generate_idea_outline_with_llm(openai_client, llm_params)
            self.idea_outline = outline
            return outline
        except Exception as e:
            logger.warning(f"Failed to generate idea outline of {self.url}: {e}")
            self.idea_outline = {}
            return {}

    def _generate_ideas_with_llm(
        self,
        openai_client: OpenAI,
        llm_params: dict,
        idea_config: dict,
        corpus: list["CorpusPaper"],
    ) -> list[str]:
        if not self.abstract and not self.full_text:
            logger.warning(f"Neither full text nor abstract is provided for {self.url}")
            return []

        lang = llm_params.get("language", "English")
        max_ideas = idea_config.get("max_num", 3)
        focus = idea_config.get("focus") or (
            "Generate practical ideas inspired by the paper, including follow-up research ideas, "
            "how to improve current work, and concrete experiments or applications to try."
        )
        context_size = idea_config.get("context_paper_num", 5)
        recent_context = corpus[:context_size]

        prompt = (
            f"You are given a new paper and the user's recent Zotero reading context.\n"
            f"Please generate {max_ideas} concise, practical ideas in {lang}.\n"
            "The ideas must cover fixed categories when possible: research idea, engineering idea, workflow idea. "
            "If max_ideas is larger, add one extra experiment or application idea.\n"
            "Return a JSON array of strings only.\n\n"
            f"Focus preference:\n{focus}\n\n"
        )

        if self.title:
            prompt += f"Paper title:\n{self.title}\n\n"
        if self.tldr:
            prompt += f"Paper TLDR:\n{self.tldr}\n\n"
        if self.idea_outline:
            prompt += (
                "Structured notes:\n"
                f"- Problem: {self.idea_outline.get('problem', '')}\n"
                f"- Method: {self.idea_outline.get('method', '')}\n"
                f"- Finding: {self.idea_outline.get('finding', '')}\n"
                f"- Limitation: {self.idea_outline.get('limitation', '')}\n\n"
            )
        if self.abstract:
            prompt += f"Paper abstract:\n{self.abstract}\n\n"
        if self.full_text:
            prompt += f"Paper content preview:\n{self.full_text}\n\n"
        if recent_context:
            prompt += "Recent Zotero context:\n"
            for idx, paper in enumerate(recent_context, start=1):
                prompt += f"{idx}. {paper.title}\nAbstract: {paper.abstract}\n\n"

        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        prompt_tokens = prompt_tokens[:5000]
        prompt = enc.decode(prompt_tokens)

        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant who turns scientific papers into practical ideas with fixed categories. "
                        "Return only a JSON array of short idea strings, with no markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get("generation_kwargs", {})
        )
        ideas = _extract_json_payload(response.choices[0].message.content)
        if not isinstance(ideas, list):
            raise ValueError("Ideas response is not a list")
        ideas = [str(idea).strip() for idea in ideas if str(idea).strip()]
        return ideas[:max_ideas]

    def generate_ideas(
        self,
        openai_client: OpenAI,
        llm_params: dict,
        idea_config: dict,
        corpus: list["CorpusPaper"],
    ) -> list[str]:
        try:
            ideas = self._generate_ideas_with_llm(openai_client, llm_params, idea_config, corpus)
            self.ideas = ideas
            return ideas
        except Exception as e:
            logger.warning(f"Failed to generate ideas of {self.url}: {e}")
            self.ideas = []
            return []

    def _generate_affiliations_with_llm(self, openai_client:OpenAI,llm_params:dict) -> Optional[list[str]]:
        if self.full_text is not None:
            prompt = f"Given the beginning of a paper, extract the affiliations of the authors in a python list format, which is sorted by the author order. If there is no affiliation found, return an empty list '[]':\n\n{self.full_text}"
            # use gpt-4o tokenizer for estimation
            enc = tiktoken.encoding_for_model("gpt-4o")
            prompt_tokens = enc.encode(prompt)
            prompt_tokens = prompt_tokens[:2000]  # truncate to 2000 tokens
            prompt = enc.decode(prompt_tokens)
            affiliations = openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant who perfectly extracts affiliations of authors from a paper. You should return a python list of affiliations sorted by the author order, like [\"TsingHua University\",\"Peking University\"]. If an affiliation is consisted of multi-level affiliations, like 'Department of Computer Science, TsingHua University', you should return the top-level affiliation 'TsingHua University' only. Do not contain duplicated affiliations. If there is no affiliation found, you should return an empty list [ ]. You should only return the final list of affiliations, and do not return any intermediate results.",
                    },
                    {"role": "user", "content": prompt},
                ],
                **llm_params.get('generation_kwargs', {})
            )
            affiliations = affiliations.choices[0].message.content

            affiliations = re.search(r'\[.*?\]', affiliations, flags=re.DOTALL).group(0)
            affiliations = json.loads(affiliations)
            affiliations = list(set(affiliations))
            affiliations = [str(a) for a in affiliations]

            return affiliations
    
    def generate_affiliations(self, openai_client:OpenAI,llm_params:dict) -> Optional[list[str]]:
        try:
            affiliations = self._generate_affiliations_with_llm(openai_client,llm_params)
            self.affiliations = affiliations
            return affiliations
        except Exception as e:
            logger.warning(f"Failed to generate affiliations of {self.url}: {e}")
            self.affiliations = None
            return None


def generate_daily_summary(
    papers: list[Paper],
    openai_client: OpenAI,
    llm_params: dict,
    idea_config: dict,
) -> list[str]:
    if not papers:
        return []

    lang = llm_params.get("language", "English")
    max_items = idea_config.get("daily_summary_num", 3)
    focus = idea_config.get("focus") or "Prioritize practical, high-leverage directions."
    prompt = (
        f"Summarize today's recommended papers into {max_items} actionable directions in {lang}.\n"
        "Each direction should be one sentence and should describe what the user should try next.\n"
        "Return a JSON array of strings only.\n\n"
        f"Focus preference:\n{focus}\n\n"
    )
    for idx, paper in enumerate(papers, start=1):
        prompt += f"{idx}. {paper.title}\n"
        prompt += f"TLDR: {paper.tldr or ''}\n"
        if paper.idea_outline:
            prompt += (
                f"Problem: {paper.idea_outline.get('problem', '')}\n"
                f"Method: {paper.idea_outline.get('method', '')}\n"
                f"Finding: {paper.idea_outline.get('finding', '')}\n"
                f"Limitation: {paper.idea_outline.get('limitation', '')}\n"
            )
        if paper.ideas:
            prompt += f"Candidate ideas: {'; '.join(paper.ideas)}\n"
        prompt += "\n"

    enc = tiktoken.encoding_for_model("gpt-4o")
    prompt = enc.decode(enc.encode(prompt)[:6000])
    try:
        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You synthesize a set of papers into a short set of next actions. "
                        "Return JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get("generation_kwargs", {})
        )
        summary = _extract_json_payload(response.choices[0].message.content)
        if not isinstance(summary, list):
            raise ValueError("Daily summary response is not a list")
        return [str(item).strip() for item in summary if str(item).strip()][:max_items]
    except Exception as e:
        logger.warning(f"Failed to generate daily summary: {e}")
        fallback = []
        for paper in papers[:max_items]:
            if paper.ideas:
                fallback.append(paper.ideas[0])
        return fallback


@dataclass
class CorpusPaper:
    title: str
    abstract: str
    added_date: datetime
    paths: list[str]
