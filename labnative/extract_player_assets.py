from pathlib import Path
from PIL import Image
import io, json, struct, sys

actbin=Path(sys.argv[1])
out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)
data=actbin.read_bytes()

wall_hdr=b"MODULE_WALL_____"
p=data.find(wall_hdr)
if p<0:
    raise SystemExit("MODULE_WALL not found")
base=p+16
count=struct.unpack_from("<I",data,base)[0]
meta=base+8
if count<=8:
    raise SystemExit(f"wall count too small: {count}")

def extract_wall(i:int):
    width,height,ptr=struct.unpack_from("<HHI",data,meta+i*12)
    png_size,png_w,png_h=struct.unpack_from("<III",data,ptr)
    blob=data[ptr+12:ptr+12+png_size]
    if not blob.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"wall {i} invalid PNG")
    im=Image.open(io.BytesIO(blob)).convert("RGBA")
    pix=im.load()
    changed=0
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a=pix[x,y]
            if r>=248 and g<=8 and b>=248:
                pix[x,y]=(r,g,b,0)
                changed+=1
    path=out/f"wall_{i:03d}.png"
    im.save(path,optimize=True)
    return {
        "id":i,"logical_width":width,"logical_height":height,
        "png_width":png_w,"png_height":png_h,"png_size":png_size,
        "transparent_key_pixels":changed,"path":path.name
    }

items=[extract_wall(8),extract_wall(9)]
(out/"player-atlas-metadata.json").write_text(json.dumps(items,indent=2),encoding="utf-8")
print(json.dumps(items,indent=2))
