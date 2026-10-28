"""Grounded mission handoffs. Tool measurements are separate from AI hypotheses."""
from typing import Literal
import unicodedata
from pydantic import BaseModel,ConfigDict,Field
from app.public_web import inspect_html


class CitationMismatch(ValueError):
    pass


def normalize_quote(text):
    """Normalize typography and spacing, never words, case, numbers or negation."""
    text=unicodedata.normalize("NFC",text).translate(str.maketrans({
        "\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',"\u2013":"-","\u2014":"-","\u2011":"-"}))
    return " ".join(text.split())


class Opportunity(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title:str=Field(min_length=8,max_length=120)
    source_id:str=Field(min_length=2,max_length=20)
    quote:str=Field(min_length=12,max_length=240)
    hypothesis:str=Field(min_length=20,max_length=450)
    proposed_action:str=Field(min_length=20,max_length=400)
    success_check:str=Field(min_length=15,max_length=300)
    priority:Literal["high","medium","low"]="medium"
    existing_coverage:str=Field(default="",max_length=450)
    why_change:str=Field(default="",max_length=450)


class Strength(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title:str=Field(min_length=5,max_length=120)
    source_id:str=Field(min_length=2,max_length=20)
    quote:str=Field(min_length=12,max_length=240)
    why_keep:str=Field(min_length=15,max_length=400)


class MissionPlan(BaseModel):
    model_config=ConfigDict(extra="forbid")
    summary:str=Field(min_length=20,max_length=700)
    opportunities:list[Opportunity]=Field(min_length=1,max_length=3)
    unknowns:list[str]=Field(min_length=1,max_length=5)
    strengths:list[Strength]=Field(default_factory=list,max_length=5)
    coverage_notes:list[str]=Field(default_factory=list,max_length=6)


def validate_plan(data,sources):
    plan=MissionPlan.model_validate(data)
    evidence={source["id"]:normalize_quote(source["text"]) for source in sources}
    for item in [*plan.opportunities,*plan.strengths]:
        if item.source_id not in evidence or normalize_quote(item.quote) not in evidence[item.source_id]:
            raise CitationMismatch("Opportunity quote does not match the collected source")
    return plan.model_dump()


def technical_checks(sources):
    checks=[]
    for source in sources:
        s=source["signals"]
        measurements=[("Inquiry forms",s["forms"]>0,f'{s["forms"]} HTML forms found'),
          ("Direct contact links",sum(s[k] for k in ("phone_links","email_links","whatsapp_links"))>0,
           f'{s["phone_links"]} telephone, {s["email_links"]} email and {s["whatsapp_links"]} WhatsApp links'),
          ("Mobile viewport",s["viewport"],"Viewport metadata present" if s["viewport"] else "No viewport metadata found"),
          ("Image descriptions",s["images_without_alt"]==0,f'{s["images_without_alt"]} of {s["images"]} images lack nonempty alt text')]
        checks.extend({"source_id":source["id"],"name":name,"passed":passed,"detail":detail} for name,passed,detail in measurements)
    return checks


def sample_source():
    html='<title>Sample Workshop</title><h1>Made-to-order furniture</h1><p>We build custom furniture. Discuss your requirements with our workshop.</p>'
    return {"id":"S1","url":"https://example.org/sentinelx-sample-workshop","role":"business",
            "origin":"fixture","collected_at":None,"sha256":None,"bytes":len(html),**inspect_html(html)}


def sample_plan():
    return {"summary":"Sample mission: clarify how a visitor can request a custom-furniture consultation.",
      "strengths":[{"title":"A clear made-to-order offering","source_id":"S1","quote":"We build custom furniture.",
                    "why_keep":"Preserve this simple description so visitors can identify the workshop's service."}],
      "coverage_notes":["Text and HTML checks use a sample fixture. No real image, video, device layout or website was inspected."],
      "opportunities":[{"title":"Make consultation requests easier to start","source_id":"S1",
        "quote":"Discuss your requirements with our workshop.",
        "hypothesis":"Visitors may need a clearer inquiry path. This is a sample hypothesis, not a measured cause of lost inquiries.",
        "proposed_action":"Prepare a page describing the consultation process and a working inquiry form.",
        "success_check":"After approval, check that the public page loads and a labeled synthetic inquiry is stored.",
        "priority":"medium","existing_coverage":"The sample asks visitors to discuss requirements but does not describe the next step.",
        "why_change":"A precise inquiry instruction is a testable improvement; no sales uplift is established."}],
      "unknowns":["No real website was retrieved in sample mode.","Traffic, sales and conversion impact have not been measured."]}


def report_markdown(payload):
    plan=payload.get("plan") or {}
    lines=["# SentinelX website report","",f'Provenance: {payload["provenance"]}',
           "Claims and recommendations require owner review. No business impact has been measured.","",plan.get("summary","Report incomplete"),
           "","## What works"]
    for item in plan.get("strengths",[]):
        lines.extend(["", "### "+item["title"],item["why_keep"],f'> {item["quote"]} (source {item["source_id"]})'])
    lines.extend(["","## What to change and why"])
    for item in plan.get("opportunities",[]):
        lines.extend(["","### "+item["title"],"Priority: "+item.get("priority","review"),item["hypothesis"],
           "Already present: "+item.get("existing_coverage","Not recorded in this older report"),
           "Why: "+item.get("why_change","Review hypothesis"),"Proposed change: "+item["proposed_action"],
           "Verification: "+item["success_check"],f'> {item["quote"]} (source {item["source_id"]})'])
    lines.extend(["","## Sources and coverage"])
    for source in payload["sources"]:
        lines.extend([f'- {source["id"]}: {source["url"]}',f'  Origin: {source["origin"]}; collected: {source.get("collected_at")}; SHA-256: {source.get("sha256")}'])
    lines.extend(["- "+note for note in plan.get("coverage_notes",[])])
    lines.extend(["","## Attached media reviews and documents"])
    for asset in payload.get("assets",[]):
        lines.extend(["","### "+asset.get("filename",asset["kind"]),"Provenance: "+asset["provenance"],asset["limitation"],asset["text"]])
    lines.extend(["","## Unknowns and limits",*["- "+note for note in [*plan.get("unknowns",[]),*payload.get("limitations",[])]]])
    return "\n".join(lines)
