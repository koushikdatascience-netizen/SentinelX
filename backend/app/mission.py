"""Grounded mission handoffs. Tool measurements are separate from AI hypotheses."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from app.public_web import inspect_html


class Opportunity(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title:str=Field(min_length=8,max_length=120)
    source_id:str=Field(min_length=2,max_length=20)
    quote:str=Field(min_length=12,max_length=240)
    hypothesis:str=Field(min_length=20,max_length=450)
    proposed_action:str=Field(min_length=20,max_length=400)
    success_check:str=Field(min_length=15,max_length=300)


class MissionPlan(BaseModel):
    model_config=ConfigDict(extra="forbid")
    summary:str=Field(min_length=20,max_length=700)
    opportunities:list[Opportunity]=Field(min_length=1,max_length=3)
    unknowns:list[str]=Field(min_length=1,max_length=5)


def validate_plan(data,sources):
    plan=MissionPlan.model_validate(data)
    evidence={source["id"]:" ".join(source["text"].split()) for source in sources}
    for item in plan.opportunities:
        if item.source_id not in evidence or " ".join(item.quote.split()) not in evidence[item.source_id]:
            raise ValueError("Opportunity quote does not match the collected source")
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
      "opportunities":[{"title":"Make consultation requests easier to start","source_id":"S1",
        "quote":"Discuss your requirements with our workshop.",
        "hypothesis":"Visitors may need a clearer inquiry path. This is a sample hypothesis, not a measured cause of lost inquiries.",
        "proposed_action":"Prepare a page describing the consultation process and a working inquiry form.",
        "success_check":"After approval, check that the public page loads and a labeled synthetic inquiry is stored."}],
      "unknowns":["No real website was retrieved in sample mode.","Traffic, sales and conversion impact have not been measured."]}
