"""Local, relevance-ranked retrieval from consented owner knowledge assets."""
import hashlib
import json
import re
from sqlalchemy import select
from app.business_store import BrandAsset


def retrieve(documents,query,limit=6):
    terms=set(re.findall(r"[\w]+",query.casefold()))-{ "the","and","for","what","with","that","this","your","business"}
    chunks=[];seen=set()
    for document in documents:
        if document.sha256 in seen:continue
        seen.add(document.sha256)
        metadata=json.loads(document.metadata_json)
        text=metadata.get("knowledge_text") or metadata.get("text_excerpt","")
        if metadata.get("dataset_profile"):text="Local dataset profile (saved values; verify source):\n"+json.dumps(metadata["dataset_profile"],ensure_ascii=False)+"\n"+text
        for index,start in enumerate(range(0,min(len(text),80000),600)):
            excerpt=text[start:start+800]
            words=set(re.findall(r"[\w]+",(document.filename+" "+excerpt).casefold()))
            score=len(terms&words)+(0.2 if index==0 else 0)
            chunks.append((score,document.created_at.timestamp(),{"id":"K"+document.id.replace("-","")[:9]+"C"+str(index),"asset_id":document.id,"filename":document.filename,"sha256":document.sha256,"text":excerpt,"origin":"user_supplied","coverage":metadata.get("limitation","Owner-supplied material; not independently verified")}))
    chunks.sort(key=lambda entry:(-entry[0],-entry[1],entry[2]["id"]))
    return [entry[2] for entry in chunks[:limit]]


def workspace_sources(db,workspace_id,query,limit=6):
    documents=db.scalars(select(BrandAsset).where(BrandAsset.workspace_id==workspace_id,BrandAsset.kind.in_(["document","knowledge"])).order_by(BrandAsset.created_at.desc()).limit(50)).all()
    return retrieve(documents,query,limit)
