"""Bounded business uploads; original bytes and observations keep distinct provenance."""
import hashlib
import io
import json
import re
import zipfile
from pathlib import PurePath
from xml.etree import ElementTree
from PIL import Image
from sqlalchemy import select,func
from app.business_store import BrandAsset
from app.workspace_store import Workspace

MAX_FILE=8_000_000
MAX_STORAGE=80_000_000
DOCUMENTS={".pdf":"application/pdf",".txt":"text/plain",".csv":"text/csv",
           ".docx":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
           ".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def image_info(payload):
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.width*image.height>20_000_000 or image.format not in ("PNG","JPEG","WEBP","ICO"):
                raise ValueError("Use PNG, JPEG or WebP up to 20 megapixels")
            image.load()
            mime=Image.MIME.get(image.format,"image/png")
            return mime,{"width":image.width,"height":image.height}
    except (OSError,Image.DecompressionBombError) as exc:
        raise ValueError("Invalid image file") from exc


def validate_upload(payload,filename,kind):
    if not 0<len(payload)<=MAX_FILE:raise ValueError("Files must be 1 byte to 8 MB")
    name=re.sub(r"[^a-zA-Z0-9_. -]","_",PurePath(filename.replace("\\","/")).name)[:180] or "business-file"
    if kind=="logo" or name.lower().endswith((".png",".jpg",".jpeg",".webp")):
        mime,metadata=image_info(payload)
        return name,mime,metadata
    suffix=PurePath(name).suffix.lower()
    mime=DOCUMENTS.get(suffix)
    if not mime:raise ValueError("Use PNG, JPEG, WebP, PDF, TXT, CSV, DOCX or XLSX; executable and macro files are not accepted")
    text=""
    if suffix in (".txt",".csv"):
        text=payload.decode("utf-8-sig")
        if "\x00" in text:raise ValueError("Invalid text file")
    elif suffix==".pdf":
        if not payload.startswith(b"%PDF-"):raise ValueError("Invalid PDF")
        from pypdf import PdfReader
        try:
            reader=PdfReader(io.BytesIO(payload))
            if reader.is_encrypted:raise ValueError("Encrypted PDFs are not supported")
            text="\n".join((page.extract_text() or "")[:4000] for page in reader.pages[:20])
        except Exception as exc:raise ValueError("PDF could not be read; upload an unencrypted business document") from exc
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                entries=archive.infolist()
                if len(entries)>1000 or sum(item.file_size for item in entries)>20_000_000:
                    raise ValueError("Office document expands beyond limits")
                if any("vbaproject" in item.filename.lower() or item.flag_bits&1 for item in entries):
                    raise ValueError("Encrypted or macro documents are not supported")
                target="word/document.xml" if suffix==".docx" else "xl/sharedStrings.xml"
                if suffix==".xlsx" and target not in archive.namelist():
                    target=next((item.filename for item in entries if item.filename.startswith("xl/worksheets/") and item.filename.endswith(".xml")),"")
                text=" ".join(ElementTree.fromstring(archive.read(target)).itertext())
        except (KeyError,zipfile.BadZipFile,ElementTree.ParseError) as exc:raise ValueError("Invalid Office document") from exc
    return name,mime,{"text_excerpt":text[:8000],"limitation":"Owner-supplied content; not independently verified. Text extraction is bounded; image-only documents may have no extracted text."}


def store_asset(db,workspace_id,kind,filename,mime,payload,*,source_url="",job_id=None,metadata=None,supplied_hash=None):
    digest=hashlib.sha256(payload).hexdigest()
    if supplied_hash is not None and supplied_hash!=digest:raise ValueError("Supplied SHA-256 does not match actual file bytes")
    db.scalar(select(Workspace).where(Workspace.id==workspace_id).with_for_update())
    previous=db.scalar(select(BrandAsset).where(BrandAsset.workspace_id==workspace_id,BrandAsset.sha256==digest,BrandAsset.kind==kind))
    if previous:return previous
    used=db.scalar(select(func.coalesce(func.sum(func.length(BrandAsset.content)),0)).where(BrandAsset.workspace_id==workspace_id))
    if used+len(payload)>MAX_STORAGE:raise ValueError("Workspace asset storage limit of 80 MB reached")
    row=BrandAsset(workspace_id=workspace_id,job_id=job_id,kind=kind,filename=filename[:180],mime=mime,
        sha256=digest,content=payload,source_url=source_url,metadata_json=json.dumps(metadata or {}))
    db.add(row);db.flush()
    return row


def asset_info(row):
    return {"id":row.id,"kind":row.kind,"filename":row.filename,"mime":row.mime,"sha256":row.sha256,
        "bytes":len(row.content),"source_url":row.source_url,"created_at":row.created_at.isoformat(),
        "provenance":"user_supplied" if not row.job_id else "source_observed",
        "metadata":json.loads(row.metadata_json)}
