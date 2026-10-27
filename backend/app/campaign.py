"""Bounded seven-day campaign contracts and offline, explicitly sample fixtures."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Platform=Literal["instagram","facebook","whatsapp"]
Language=Literal["en","bn","hi"]

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid")

class Gap(Strict):
    finding: str=Field(min_length=10,max_length=240)
    evidence_id: str | None = None
    assumption: bool

class CampaignAudit(Strict):
    offer_summary: str=Field(min_length=10,max_length=500)
    audience_guess: str=Field(min_length=5,max_length=350)
    gaps: list[Gap]=Field(min_length=1,max_length=5)
    positioning_angles: list[str]=Field(min_length=3,max_length=3)

class DayPlan(Strict):
    day: int=Field(ge=1,le=7)
    platform: Platform
    post_type: str=Field(min_length=3,max_length=70)
    caption: str=Field(min_length=10,max_length=1500)
    hashtags: list[str]=Field(max_length=12)
    cta: str=Field(min_length=5,max_length=180)
    creative_brief: str=Field(min_length=10,max_length=600)
    evidence_ids: list[str]=Field(max_length=5)

class SevenDayPlan(Strict):
    items: list[DayPlan]=Field(min_length=7,max_length=7)
    @model_validator(mode="after")
    def unique_days(self):
        if sorted(i.day for i in self.items)!=list(range(1,8)):
            raise ValueError("Campaign requires exactly days 1–7")
        return self

class CampaignGeneration(Strict):
    audit: CampaignAudit
    plan: SevenDayPlan

# Returns a review flag rather than silently deleting claims.
UNSUPPORTED=re.compile(r"\b(?:\d+(?:\.\d+)?\s*%\s*(?:increase|growth|discount|better)|"
                       r"(?:revenue|sales|profit|earnings)\s*(?:grew|rose|up|by|of)\s*\d+|"
                       r"(?:guaranteed|certified|award.winning|number\s*one))\b",re.IGNORECASE)
def unsupported_claims(text:str)->list[str]:
    return list(dict.fromkeys(m.group(0) for m in UNSUPPORTED.finditer(text)))

def sample_plan(description:str,goal:str,language:Language,platforms:list[Platform])->tuple[dict,dict]:
    # User input is NOT established truth. These are clearly SAMPLE marketing drafts.
    summaries={
        "en":("Example positioning based on unverified owner input",
              "Potential customers seeking a customized product",
              "Confirm product specifications and response process",
              "Ask about customization options",
              "Request a quotation"),
        "bn":("মালিকের যাচাই না-করা তথ্যের ভিত্তিতে উদাহরণ প্রচার পরিকল্পনা",
              "নিজের পছন্দমতো পণ্য খুঁজছেন এমন সম্ভাব্য ক্রেতা",
              "পণ্যের তথ্য ও যোগাযোগের প্রক্রিয়া যাচাই করুন",
              "কাস্টমাইজেশনের সুবিধা সম্পর্কে জানুন",
              "মূল্য জানতে যোগাযোগ করুন"),
        "hi":("मालिक की अप्रमाणित जानकारी के आधार पर उदाहरण योजना",
              "अपनी जरूरत के अनुसार उत्पाद खोजने वाले संभावित ग्राहक",
              "उत्पाद जानकारी और संपर्क प्रक्रिया की पुष्टि करें",
              "कस्टम विकल्पों के बारे में पूछें",
              "मूल्य जानने के लिए संपर्क करें")
    }
    title,audience,issue,caption,cta=summaries[language]
    audit={"offer_summary":title,"audience_guess":audience,
           "gaps":[{"finding":issue,"evidence_id":None,"assumption":True}],
           "positioning_angles":[caption,cta,title]}
    items=[{"day":d,"platform":platforms[(d-1)%len(platforms)],
            "post_type":"sample educational post",
            "caption":caption+f" — {d}" ,"hashtags":["#SentinelXSample"],"cta":cta,
            "creative_brief":title+f" — sample visual concept for day {d}.",
            "evidence_ids":[]} for d in range(1,8)]
    return audit,{"items":items}
