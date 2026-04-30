"""Optional LLM-powered content generation for JiraOps."""
from __future__ import annotations

import json
import sys
from typing import Any

import requests

from tools.jira.formatters import report_to_prompt_data


STORY_SYSTEM_PROMPT = """\
You are a senior technical program manager writing a Jira story. \
Given a brief summary, generate a well-structured story description in markdown format.

Your output MUST include these sections:

1. **Objective** — 2-3 sentences explaining the goal and why this work matters.

2. **Background** — Brief context on why this is needed. What problem does it solve? \
What triggered this request?

3. **Scope** — Bullet list of what is in scope for this story.

4. **Acceptance Criteria** — Numbered list of specific, testable criteria that define \
"done". Each criterion should be concrete and verifiable.

5. **Technical Notes** (optional) — Any implementation hints, constraints, or \
dependencies worth noting. Only include if relevant.

Guidelines:
- Be specific and actionable, not vague.
- Write acceptance criteria that a QA engineer could verify.
- Keep it concise — no filler text.
- Use professional language appropriate for engineering teams.
- Do NOT invent technical details you can't infer from the summary.
- If the summary is vague, keep the story general but well-structured.
- Output ONLY the description content in markdown — no title, no metadata.
"""


SYSTEM_PROMPT = """\
You are a technical program manager writing a quarterly performance review \
designed to showcase accomplishments and highlight the impact of work delivered. \
You will receive structured data about Jira issues resolved during a quarter. \
Write a polished markdown report suitable for sharing with leadership, managers, \
or in a performance review context.

Your goal is to frame each piece of work as an achievement — emphasize the value \
delivered, problems solved, risks mitigated, and capabilities enabled. Turn raw \
issue data into a compelling narrative of what was accomplished and why it matters.

Your report MUST include:

1. **Executive Summary** — A strong opening paragraph (3-4 sentences) that captures \
the quarter's headline achievements, total volume of work delivered, and overall \
impact. Lead with the most impressive outcomes.

2. **Key Themes & Impact Areas** — Identify 3-5 strategic themes from the work \
(e.g. "system reliability improvements", "feature delivery velocity", \
"cross-team unblocking"). For each theme, write 1-2 sentences explaining the \
business impact.

3. **Accomplishments by Initiative** — Group resolved issues by epic/initiative. \
For each group, write a brief intro sentence about the initiative's goal, then \
bullet points for each issue. Frame each bullet as an achievement: what was done \
AND why it matters. Keep the Jira issue key (e.g. **NGC-123**) in each bullet.

4. **Standout Achievements** — Highlight the most impressive work: fast turnarounds \
on critical issues, high-priority blockers resolved, cross-project coordination, \
complex bugs fixed, or anything that demonstrates exceptional responsiveness, \
technical depth, or initiative. Explain why each stands out.

5. **Productivity & Quality Summary** — 2-3 sentences assessing delivery velocity, \
cycle time trends, and quality indicators (bugs fixed, stability improvements). \
End on a strong note about capabilities demonstrated.

Guidelines:
- Frame everything as accomplishments, not just tasks completed.
- Use action-oriented language: "delivered", "resolved", "unblocked", "improved", \
"eliminated", "enabled", "accelerated".
- Quantify where possible: cycle times, issue counts, turnaround speed.
- Use markdown formatting (headers, bold, bullets).
- Keep issue keys visible — they are important for traceability.
- Be specific and concrete, not generic. Reference actual issue summaries and details.
- Write in a professional, confident tone appropriate for a performance review.
- Do NOT invent issues or data that isn't in the input.
- Do NOT use filler language or generic corporate speak. Every sentence should carry \
specific information.
"""


def generate_narrative(
    report: dict,
    provider: str,
    model: str,
    *,
    ollama_base_url: str = "http://localhost:11434",
    openai_api_key: str = "",
    anthropic_api_key: str = "",
) -> str | None:
    """Generate an LLM-enhanced quarterly narrative.

    Returns markdown string on success, None on failure (caller should fall back to template).
    """
    prompt_data = report_to_prompt_data(report)

    try:
        if provider == "ollama":
            return _call_ollama(prompt_data, model, ollama_base_url)
        elif provider == "openai":
            return _call_openai(prompt_data, model, openai_api_key)
        elif provider == "anthropic":
            return _call_anthropic(prompt_data, model, anthropic_api_key)
        else:
            print(f"Unknown LLM provider: {provider}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"LLM generation failed ({provider}): {e}", file=sys.stderr)
        return None


def _call_ollama(prompt_data: str, model: str, base_url: str) -> str | None:
    model = model or "llama3"
    resp = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "system": SYSTEM_PROMPT,
            "prompt": prompt_data,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response")


def _call_openai(prompt_data: str, model: str, api_key: str) -> str | None:
    if not api_key:
        print("OPENAI_API_KEY not set", file=sys.stderr)
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("openai package not installed. Run: pip install openai", file=sys.stderr)
        return None

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model or "gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_data},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content


def _call_anthropic(prompt_data: str, model: str, api_key: str) -> str | None:
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        return None

    try:
        from anthropic import Anthropic
    except ImportError:
        print("anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        return None

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model or "claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_data}],
    )
    return resp.content[0].text


def generate_story(
    summary: str,
    issue_type: str,
    provider: str,
    model: str,
    *,
    project: str = "",
    ollama_base_url: str = "http://localhost:11434",
    openai_api_key: str = "",
    anthropic_api_key: str = "",
) -> str | None:
    """Generate a structured Jira story description from a brief summary.

    Returns markdown string on success, None on failure.
    """
    prompt = f"Issue type: {issue_type}\n"
    if project:
        prompt += f"Project: {project}\n"
    prompt += f"Summary: {summary}\n\nGenerate a well-structured description for this story."

    try:
        if provider == "ollama":
            return _call_llm_with_prompt(STORY_SYSTEM_PROMPT, prompt, "ollama", model, ollama_base_url, "", "")
        elif provider == "openai":
            return _call_llm_with_prompt(STORY_SYSTEM_PROMPT, prompt, "openai", model, "", openai_api_key, "")
        elif provider == "anthropic":
            return _call_llm_with_prompt(STORY_SYSTEM_PROMPT, prompt, "anthropic", model, "", "", anthropic_api_key)
        else:
            print(f"Unknown LLM provider: {provider}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"LLM story generation failed ({provider}): {e}", file=sys.stderr)
        return None


def _call_llm_with_prompt(
    system_prompt: str, user_prompt: str,
    provider: str, model: str,
    ollama_base_url: str, openai_api_key: str, anthropic_api_key: str,
) -> str | None:
    """Generic LLM call with configurable system and user prompts."""
    if provider == "ollama":
        model = model or "llama3"
        resp = requests.post(
            f"{ollama_base_url}/api/generate",
            json={"model": model, "system": system_prompt, "prompt": user_prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response")

    elif provider == "openai":
        if not openai_api_key:
            print("OPENAI_API_KEY not set", file=sys.stderr)
            return None
        try:
            from openai import OpenAI
        except ImportError:
            print("openai package not installed. Run: pip install openai", file=sys.stderr)
            return None
        client = OpenAI(api_key=openai_api_key)
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content

    elif provider == "anthropic":
        if not anthropic_api_key:
            print("ANTHROPIC_API_KEY not set", file=sys.stderr)
            return None
        try:
            from anthropic import Anthropic
        except ImportError:
            print("anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
            return None
        client = Anthropic(api_key=anthropic_api_key)
        resp = client.messages.create(
            model=model or "claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return resp.content[0].text

    return None
