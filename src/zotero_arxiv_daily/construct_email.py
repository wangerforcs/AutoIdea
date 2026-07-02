from .protocol import Paper
import math


framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* 调整星星大小 */
      line-height: 1; /* 确保垂直对齐 */
      display: inline-flex;
      align-items: center; /* 保持对齐 */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* 半颗星的宽度 */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
</div>

</body>
</html>
"""

def get_empty_html():
  block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  </table>
  """
  return block_template


def get_daily_summary_html(summary_items: list[dict] | list[str] | None) -> str:
    if not summary_items:
        return ""
    cards = []
    for item in summary_items:
        if isinstance(item, str):
            item = {"idea": item, "innovation": "", "feasibility": "", "evidence": [], "first_step": ""}
        evidence = item.get("evidence", [])
        evidence_html = ""
        if evidence:
            bullets = "".join(f"<li>{entry}</li>" for entry in evidence)
            evidence_html = f'<div style="margin-top: 6px;"><strong>Evidence:</strong><ul style="margin: 6px 0 0 20px; padding: 0;">{bullets}</ul></div>'
        innovation_html = f'<div style="margin-top: 6px;"><strong>Innovation:</strong> {item.get("innovation", "")}</div>' if item.get("innovation") else ""
        feasibility_html = f'<div style="margin-top: 6px;"><strong>Why it is feasible:</strong> {item.get("feasibility", "")}</div>' if item.get("feasibility") else ""
        first_step_html = f'<div style="margin-top: 6px;"><strong>First step:</strong> {item.get("first_step", "")}</div>' if item.get("first_step") else ""
        cards.append(
            """
            <li style="margin-bottom: 14px;">
                <div><strong>Idea:</strong> {idea}</div>
                {innovation}
                {feasibility}
                {evidence}
                {first_step}
            </li>
            """.format(
                idea=item.get("idea", ""),
                innovation=innovation_html,
                feasibility=feasibility_html,
                evidence=evidence_html,
                first_step=first_step_html,
            )
        )
    items = "".join(cards)
    return """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #cfe8d5; border-radius: 8px; padding: 16px; background-color: #f1faf3;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #245c35;">
            Selected Ideas for Today
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <ol style="margin: 8px 0 0 20px; padding: 0;">__ITEMS__</ol>
        </td>
    </tr>
    </table>
    """.replace("__ITEMS__", items)

def format_ideas_html(ideas: list[str] | None) -> str:
    if not ideas:
        return "<em>No ideas generated for this paper.</em>"
    idea_items = "".join(
        f'<li style="margin-bottom: 6px;">{idea}</li>'
        for idea in ideas
    )
    return f'<ol style="margin: 8px 0 0 20px; padding: 0;">{idea_items}</ol>'


def get_block_html(title:str, authors:str, rate:str, tldr:str, pdf_url:str, affiliations:str=None, ideas_html:str=''):
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors}
            <br>
            <i>{affiliations}</i>
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {tldr}
        </td>
    </tr>
    __IDEAS_ROW__

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
        </td>
    </tr>
</table>
"""
    ideas_row = ""
    if ideas_html:
        ideas_row = """
    <tr>
        <td style=\"font-size: 14px; color: #333; padding: 8px 0;\">
            <strong>Ideas:</strong> {ideas_html}
        </td>
    </tr>
""".format(ideas_html=ideas_html)
    return block_template.replace("__IDEAS_ROW__", ideas_row).format(
        title=title,
        authors=authors,
        rate=rate,
        tldr=tldr,
        pdf_url=pdf_url,
        affiliations=affiliations,
    )

def get_stars(score:float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 6
    high = 8
    if score <= low:
        return ''
    elif score >= high:
        return full_star * 5
    else:
        interval = (high-low) / 10
        star_num = math.ceil((score-low) / interval)
        full_star_num = int(star_num/2)
        half_star_num = star_num - full_star_num * 2
        return '<div class="star-wrapper">'+full_star * full_star_num + half_star * half_star_num + '</div>'


def render_email(
    papers:list[Paper],
    daily_summary: list[dict] | list[str] | None = None,
    show_per_paper_ideas: bool = False,
) -> str:
    parts = []
    if len(papers) == 0 :
        return framework.replace('__CONTENT__', get_empty_html())

    summary_html = get_daily_summary_html(daily_summary)
    if summary_html:
        parts.append(summary_html)

    for p in papers:
        #rate = get_stars(p.score)
        rate = round(p.score, 1) if p.score is not None else 'Unknown'
        author_list = [a for a in p.authors]
        num_authors = len(author_list)
        if num_authors <= 5:
            authors = ', '.join(author_list)
        else:
            authors = ', '.join(author_list[:3] + ['...'] + author_list[-2:])
        if p.affiliations is not None:
            affiliations = p.affiliations[:5]
            affiliations = ', '.join(affiliations)
            if len(p.affiliations) > 5:
                affiliations += ', ...'
        else:
            affiliations = 'Unknown Affiliation'
        ideas_html = format_ideas_html(p.ideas) if show_per_paper_ideas else ""
        parts.append(get_block_html(p.title, authors, rate, p.tldr, p.pdf_url, affiliations, ideas_html))

    content = '<br>' + '</br><br>'.join(parts) + '</br>'
    return framework.replace('__CONTENT__', content)
