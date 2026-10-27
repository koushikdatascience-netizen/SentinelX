"""One explicitly authorized billable Meta capability check, sanitized output only."""
import io
import os
import sys
from PIL import Image,ImageDraw

from app.workspace_store import init_db
from app.meta_client import MetaClient

ACK="I_ACKNOWLEDGE_ONE_PAID_REQUEST"

def synthetic_png():
    image=Image.new("RGB",(256,256),(238,236,235))
    draw=ImageDraw.Draw(image)
    draw.rectangle((60,58,195,195),fill=(185,55,48))
    output=io.BytesIO();image.save(output,format="PNG")
    return output.getvalue()

def main():
    capability=os.getenv("META_SMOKE_CAPABILITY","text")
    if capability not in {"text","vision","image"}:
        print("Invalid smoke capability",file=sys.stderr);return 2
    if os.getenv("META_SMOKE_ACK")!=ACK or not os.getenv("MODEL_API_KEY"):
        print("Explicit authorization and secret key required",file=sys.stderr);return 2
    if not MetaClient._enabled(True):
        print("All live opt-in flags must be enabled for the manual test",file=sys.stderr);return 2
    # Ephemeral CI-only app-side budget reservation; this is NOT the provider billing cap.
    init_db()
    client=MetaClient()
    try:
        if capability=="text":
            r=client.text("Answer with one short visible word.",
                          "Reply exactly OK.",{"type":"object","properties":{"answer":{"type":"string"}},
                          "required":["answer"],"additionalProperties":False})
            succeeded=bool(r["data"].get("answer"))
        elif capability=="vision":
            r=client.vision(synthetic_png(),"image/png","What color is the large rectangle? One word in JSON.",
                 {"type":"object","properties":{"color":{"type":"string"}},
                  "required":["color"],"additionalProperties":False})
            succeeded=bool(r["data"].get("color"))
        else:
            r=client.image("An original studio photograph of a handmade wooden chair on a plain backdrop.")
            import base64
            data=base64.b64decode(r["data"]["image_b64"],validate=True)
            Image.open(io.BytesIO(data)).verify()
            succeeded=bool(data)
        # No raw model content, hidden reasoning, returned image, or credentials in logs.
        print("Capability:",capability)
        print("Model:",r["model"])
        print("Live Meta provenance confirmed:",r["provenance"]=="live_meta")
        print("Usable validated response:",succeeded)
        print("One request only; compare actual spend in Meta Billing.")
        return 0 if succeeded and r["provenance"]=="live_meta" else 1
    except Exception as exc:
        print("Capability check failed:",type(exc).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
