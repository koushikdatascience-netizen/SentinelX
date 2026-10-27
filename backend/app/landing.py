"""Validated landing-page specification and autoescaped, script-free rendering."""
import re
from pathlib import Path
from typing import Literal
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Strict(BaseModel):
    model_config=ConfigDict(extra="forbid")

class Benefit(Strict):
    title:str=Field(min_length=3,max_length=70)
    text:str=Field(min_length=10,max_length=220)

class FAQ(Strict):
    question:str=Field(min_length=5,max_length=120)
    answer:str=Field(min_length=10,max_length=250)

class Testimonial(Strict):
    quote:str=Field(min_length=10,max_length=240)
    author:str=Field(min_length=2,max_length=80)
    placeholder:bool=True

class LandingSpec(Strict):
    business_name:str=Field(min_length=2,max_length=100)
    headline:str=Field(min_length=8,max_length=140)
    subheadline:str=Field(min_length=10,max_length=300)
    offer:str=Field(min_length=8,max_length=220)
    cta_label:str=Field(min_length=3,max_length=60)
    benefits:list[Benefit]=Field(min_length=3,max_length=6)
    how_it_works:list[str]=Field(min_length=3,max_length=3)
    faq:list[FAQ]=Field(min_length=3,max_length=5)
    trust_points:list[str]=Field(default_factory=list,max_length=5)
    testimonials:list[Testimonial]=Field(default_factory=list,max_length=4)
    whatsapp_number:str|None=Field(default=None,max_length=20)
    contact_note:str=Field(min_length=5,max_length=200)
    theme:Literal["modern","warm","bold"]="modern"
    accent_color:str=Field(default="#5f67df",pattern=r"^#[A-Fa-f0-9]{6}$")
    hero_image_variant_id:str|None=None
    language:Literal["en","bn","hi"]="en"

    @model_validator(mode="after")
    def require_unverified_testimonials_are_labeled(self):
        if any(not t.placeholder for t in self.testimonials):
            raise ValueError("Testimonials cannot be marked verified by generated model output")
        if self.whatsapp_number and not re.fullmatch(r"\+?[1-9]\d{7,14}",self.whatsapp_number):
            raise ValueError("WhatsApp number requires international country code")
        if any(len(s)>220 for s in self.how_it_works+self.trust_points):
            raise ValueError("Content too long")
        return self

def sample_landing(business:str,goal:str,language:str="en")->dict:
    business=(business or "Sample Business")[:100]
    copy={
      "en":("Explore customized solutions for your next project","Request a consultation and discuss your preferences before making a decision.",
            "Talk to our team","Share your requirements","Discuss available options","Receive a proposed next step",
            "How do I get started?","Use the contact form to explain what you need."),
      "bn":("আপনার প্রয়োজন অনুযায়ী বিকল্প খুঁজুন","সিদ্ধান্ত নেওয়ার আগে আপনার পছন্দ ও প্রয়োজন জানিয়ে আলোচনা করুন।",
            "যোগাযোগ করুন","আপনার প্রয়োজন জানান","সম্ভাব্য বিকল্প আলোচনা করুন","পরবর্তী পদক্ষেপ জানুন",
            "কীভাবে শুরু করব?","যোগাযোগ ফর্মে আপনার প্রয়োজন লিখুন।"),
      "hi":("अपनी जरूरत के अनुसार विकल्प खोजें","निर्णय लेने से पहले अपनी पसंद और जरूरतों के बारे में बात करें।",
            "संपर्क करें","अपनी जरूरत बताएं","उपलब्ध विकल्पों पर बात करें","अगला कदम तय करें",
            "शुरू कैसे करें?","अपनी जरूरत संपर्क फ़ॉर्म में लिखें।")
    }
    title,subtitle,cta,one,two,three,q,a=copy[language]
    return LandingSpec(business_name=business,headline=title,subheadline=subtitle,offer=title,
        cta_label=cta,benefits=[
            Benefit(title=one,text=subtitle),Benefit(title=two,text=subtitle),
            Benefit(title=three,text=subtitle)],
        how_it_works=[one,two,three],
        faq=[FAQ(question=q,answer=a),FAQ(question=q+" (2)",answer=a),FAQ(question=q+" (3)",answer=a)],
        trust_points=[],testimonials=[],whatsapp_number=None,contact_note=subtitle,
        language=language).model_dump()

ENV=Environment(loader=FileSystemLoader(str(Path(__file__).parent/"landing_templates")),
                autoescape=select_autoescape(enabled_extensions=("html",)),auto_reload=False)

def render_landing(spec:LandingSpec,slug:str,provenance:str,hero_image_data:str|None=None)->str:
    # No user-supplied CSS or HTML is accepted. All fields are escaped by Jinja.
    phone=re.sub(r"\D","",spec.whatsapp_number or "")
    if phone and not 8<=len(phone)<=15:phone=""
    return ENV.get_template(spec.theme+".html").render(**spec.model_dump(),slug=slug,
        whatsapp_link=("https://wa.me/"+phone if phone else None),
        sample=(provenance!="live_meta" and provenance!="user_edited"),
        hero_image_data=hero_image_data,
        provenance=provenance)

SECURITY_HEADERS={
    "Content-Security-Policy":"default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'",
    "X-Content-Type-Options":"nosniff",
    "Referrer-Policy":"no-referrer",
    "X-Frame-Options":"DENY",
    "Cache-Control":"no-store",
}
