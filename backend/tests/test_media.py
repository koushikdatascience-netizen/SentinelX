import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.workspace_store import init_db
import uuid
import os
os.environ.setdefault("JWT_SECRET","test-secret-for-backend-suite-at-least-32-characters")

def test_media_validation():
    init_db()
    with TestClient(app) as client:
        email=f"media-{uuid.uuid4()}@example.org"
        assert client.post("/api/v1/auth/register",json={"email":email,"password":"StrongPassword123"}).status_code==201
        token=client.post("/api/v1/auth/login",json={"email":email,"password":"StrongPassword123"}).json()["access_token"]
        auth={"Authorization":"Bearer "+token}
        img=io.BytesIO()
        Image.new("RGB",(12,10)).save(img,format="PNG")
        r=client.post("/api/v1/media/image/inspect",headers=auth,files={"file":("test.png",img.getvalue(),"image/png")})
        assert r.status_code==200,r.text
        assert r.json()["width"]==12 and r.json()["inference"]=="not_run"
        assert client.post("/api/v1/media/image/inspect",files={"file":("x.png",img.getvalue(),"image/png")}).status_code==401
        assert client.post("/api/v1/media/image/inspect",headers=auth,files={"file":("x.png",b"bad","image/png")}).status_code==415
        os.environ["SENTINELX_MODE"]="demo"
        r=client.post("/api/v1/media/voice/transcribe",headers=auth,files={"file":("x.wav",b"RIFFdemo","audio/wav")})
        assert r.status_code==200 and r.json()["transcript"] is None
