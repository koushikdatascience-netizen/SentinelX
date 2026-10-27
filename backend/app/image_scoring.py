"""Interpretable local-only image measurements. Not an aesthetic or sales-quality prediction."""
import io
from collections import Counter
from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

MAX_BYTES=5_000_000
MAX_PIXELS=20_000_000

def measure_image(payload:bytes)->dict:
    if not payload or len(payload)>MAX_BYTES:
        raise ValueError("Image must be non-empty and no larger than 5 MB")
    try:
        with Image.open(io.BytesIO(payload)) as im:
            if im.format not in ("PNG","JPEG","WEBP"):
                raise ValueError("Only PNG, JPEG and WebP formats are supported")
            width,height=im.size
            fmt=im.format
            if width*height>MAX_PIXELS:
                raise ValueError("Image exceeds pixel limit")
            im.verify()
        with Image.open(io.BytesIO(payload)) as im:
            rgb=im.convert("RGB")
            rgb.thumbnail((320,320))
            gray=rgb.convert("L")
            brightness=float(ImageStat.Stat(gray).mean[0])
            contrast=float(ImageStat.Stat(gray).stddev[0])
            edges=gray.filter(ImageFilter.FIND_EDGES)
            edge_variance=float(ImageStat.Stat(edges).var[0])
            palette=rgb.quantize(colors=5).convert("RGB")
            counter=Counter(palette.getdata())
            colors=["#%02x%02x%02x" % color for color,_ in counter.most_common(5)]
        # Interpretable technical-readiness heuristic, NOT aesthetic quality or revenue.
        resolution=min(100.0,100.0*min(width,height)/1080.0)
        exposure=max(0.0,100.0-abs(brightness-128.0)*0.9)
        tonal_range=min(100.0,contrast/65.0*100.0)
        detail=min(100.0,edge_variance/600.0*100.0)
        local_readiness=round(0.25*resolution+0.25*exposure+0.25*tonal_range+0.25*detail)
        return {
            "format":fmt,"technical_readiness":local_readiness,
            "readiness_weights":{"resolution":0.25,"exposure":0.25,"tonal_range":0.25,"texture_detail":0.25},
            "width":width,"height":height,"aspect_ratio":round(width/height,3),
            "brightness":round(brightness,2),"contrast":round(contrast,2),
            "edge_variance":round(edge_variance,2),
            "dominant_colors":colors,
            "provenance":"user_supplied",
            "measurement_method":"local_image_metrics",
            "notes":["Edge variance is a texture proxy, not a calibrated blur score.",
                     "Technical readiness is a reproducible heuristic, not a validated aesthetic or conversion score.",
                     "Scoring uses fixed reference targets (1080 px, 128 brightness, 65 contrast, 600 edge variance); thresholds need calibration."]
        }
    except Image.DecompressionBombError as exc:
        raise ValueError("Image exceeds safety pixel limit") from exc
    except (UnidentifiedImageError,OSError) as exc:
        raise ValueError("Unreadable image") from exc
