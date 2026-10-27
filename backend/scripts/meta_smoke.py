"""One explicitly authorized capability request through MetaClient; no retries."""
import io
import os
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from app.meta_client import MetaClient


def main():
    if os.getenv("META_SMOKE_ACK") != "I_ACKNOWLEDGE_ONE_PAID_REQUEST":
        print("ERROR: explicit single-call authorization required",file=sys.stderr)
        return 2
    capability=os.getenv("META_SMOKE_CAPABILITY","text")
    if capability not in {"text","vision","image"}:
        print("ERROR: unsupported smoke capability",file=sys.stderr)
        return 2
    if any(os.getenv(k)!=v for k,v in {"INFERENCE_PROVIDER":"meta","ALLOW_PAID_INFERENCE":"true",
                                       "ENABLE_LIVE_MULTIMODAL":"true"}.items()) or not os.getenv("MODEL_API_KEY"):
        print("ERROR: live flags and key must be explicitly configured",file=sys.stderr)
        return 2
    # Ephemeral CI accounting only; refuse to add test tenants to an application DB.
    if os.getenv("DATABASE_URL") != "sqlite:///./meta-smoke.sqlite3":
        print("ERROR: dedicated smoke accounting database required",file=sys.stderr)
        return 2
    try:
        from app.workspace_store import init_db,SessionLocal,User,Workspace,WorkflowRun
        from app.budget import ApiBudget
        init_db()
        with SessionLocal.begin() as db:
            user=User(email=f"smoke-{uuid4()}@example.invalid",password_hash="not-a-login")
            db.add(user);db.flush()
            workspace=Workspace(owner_id=user.id,name="Ephemeral smoke")
            db.add(workspace);db.flush()
            run=WorkflowRun(workspace_id=workspace.id,website="https://example.invalid",objective="Authorized capability probe")
            db.add(run);db.flush()
            scope={"owner_id":user.id,"workspace_id":workspace.id,"run_id":run.id}
        client=MetaClient(**scope,max_tokens=128)
        if capability=="text":
            result=client.text("Reply only with OK.","Connection probe: reply OK.")
        elif capability=="vision":
            image=io.BytesIO();Image.new("RGB",(64,64),(255,0,0)).save(image,format="PNG")
            result=client.vision(image.getvalue(),"image/png","Name this square's dominant color in one word.")
        else:
            result=client.image("A plain blue circle on a white background, no text.","1024x1024")
        if result["provenance"]!="live_meta" or not result["data"]:
            raise ValueError("Not a live usable result")
        print("Capability:",capability)
        print("Provenance:",result["provenance"])
        print("Model:",result["model"])
        print("Usable output:",True)
        usage=result.get("usage") or {}
        for field in ("prompt_tokens","completion_tokens","reasoning_tokens"):
            value=usage.get(field)
            print(field+":",value if isinstance(value,int) else "unknown")
        print("Smoke succeeded. Check provider billing; reservations are not actual charges.")
        return 0
    except Exception as error:
        print("Smoke failed:",type(error).__name__,"No retry made.",file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
