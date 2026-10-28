"""Real Chromium render check with authored bytes and no external requests or model calls."""
import io
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from app.brand_capture import screenshots


def main():
    image=io.BytesIO();Image.new("RGB",(100,100),"#4056a1").save(image,format="PNG")
    class FixtureAccess:
        def get(self,url):
            if url!="https://capture.example/logo.png":raise ValueError("Fixture blocks every other resource")
            return {"url":url,"mime":"image/png","content":image.getvalue()}
    raw={"url":"https://capture.example/","mime":"text/html","content":b'<!doctype html><title>Offline capture check</title><style>body{margin:0;background:#eef1ff}h1{color:#243963;padding:30px}img{width:100px}</style><h1>Fixture Workshop</h1><img src="/logo.png"><script>document.body.innerHTML="Scripts must never run"</script><iframe src="http://127.0.0.1/private"></iframe>'}
    shots=screenshots(raw,FixtureAccess())
    assert [shot["viewport"] for shot in shots]==["desktop","mobile"]
    for shot,width in zip(shots,(1440,390)):
        with Image.open(io.BytesIO(shot["content"])) as rendered:
            assert rendered.width==width and rendered.height>500
        assert len(shot["content"])>1000 and not shot["clipped"]
    print("PASS: Chromium desktop and mobile screenshots rendered from offline fixtures; no website or model requests.")


if __name__=="__main__":main()
