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
        return {
            "width":width,"height":height,"aspect_ratio":round(width/height,3),
            "brightness":round(brightness,2),"contrast":round(contrast,2),
            "edge_variance":round(edge_variance,2),
            "dominant_colors":colors,
            "provenance":"local_measurement",
            "notes":["Edge variance is a texture proxy, not a calibrated blur score.",
                     "Local image measurements do not prove product appeal or conversion."]
        }
    except Image.DecompressionBombError as exc:
        raise ValueError("Image exceeds safety pixel limit") from exc
    except (UnidentifiedImageError,OSError) as exc:
        raise ValueError("Unreadable image") from exc
