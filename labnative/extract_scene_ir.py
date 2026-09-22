from __future__ import annotations
import argparse, base64, io, json, struct, zlib
from pathlib import Path
from PIL import Image

def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]

def f32_bits(v: int) -> float:
    return struct.unpack("<f", struct.pack("<I", v))[0]

def find_header(data: bytes, sig: bytes) -> int:
    off=data.find(sig)
    if off < 0:
        raise ValueError(f"missing ACTKOOL section {sig!r}")
    return off

def key_magenta(im: Image.Image) -> Image.Image:
    im=im.convert("RGBA")
    px=im.load()
    for y in range(im.height):
        for x in range(im.width):
            r,g,b,a=px[x,y]
            if r >= 248 and g <= 8 and b >= 248:
                px[x,y]=(r,g,b,0)
    return im

def parse_wall_table(data: bytes):
    off=find_header(data,b"MODULE_WALL_____")
    base=off+16
    count=u32(data,base)
    meta=base+8
    walls=[]
    for i in range(count):
        logical_w,logical_h,ptr=struct.unpack_from("<HHI",data,meta+i*12)
        png_size,png_w,png_h=struct.unpack_from("<III",data,ptr)
        walls.append({
            "id":i,"logical_w":logical_w,"logical_h":logical_h,
            "png_w":png_w,"png_h":png_h,"ptr":ptr,"png_size":png_size
        })
    return walls

def extract_wall(data: bytes, walls, wall_id: int) -> Image.Image:
    w=walls[wall_id]
    blob=data[w["ptr"]+12:w["ptr"]+12+w["png_size"]]
    if not blob.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"wall {wall_id} is not PNG")
    return key_magenta(Image.open(io.BytesIO(blob)))

def parse_tilelists(data: bytes):
    off=find_header(data,b"PLUGIN_TILELIST_")
    base=off+16
    count=u32(data,base)
    result=[]
    for i in range(count):
        ro=base+4+i*24
        zero,packed,cell_count,wall_id,attr_ptr,group_ptr=struct.unpack_from("<6I",data,ro)
        width=packed & 0xffff
        height=(packed >> 16) & 0xffff
        if width*height != cell_count:
            raise ValueError(f"tilelist {i}: dimension mismatch")
        result.append({
            "index":i,"width":width,"height":height,"cell_count":cell_count,
            "wall_id":wall_id,"attr_ptr":attr_ptr,"group_ptr":group_ptr
        })
    return result

def tile_attr(data: bytes, tilelist: dict, code: int):
    if code == 0:
        return 0
    x=code & 0xffff
    y=(code >> 16) & 0xffff
    if x >= tilelist["width"] or y >= tilelist["height"]:
        return None
    idx=y*tilelist["width"]+x
    return u32(data,tilelist["attr_ptr"]+idx*68)

def encode_cells(cells):
    raw=struct.pack("<%dI" % len(cells),*cells)
    return {
        "encoding":"zlib+base64+u32le",
        "count":len(cells),
        "data":base64.b64encode(zlib.compress(raw,9)).decode("ascii")
    }

def parse_gadgets(data: bytes, layer_ptr: int, grid_ptr: int):
    list_ptr=u32(data,layer_ptr+20)
    if not (0 < list_ptr < grid_ptr):
        return []
    count=u32(data,list_ptr)
    end=list_ptr+4+count*40
    if end > grid_ptr:
        raise ValueError(f"gadget list overruns tile grid at 0x{layer_ptr:x}")
    result=[]
    for i in range(count):
        vals=struct.unpack_from("<10I",data,list_ptr+4+i*40)
        result.append({
            "id":vals[0],
            "flags":vals[1],
            "x":f32_bits(vals[2]),
            "y":f32_bits(vals[3]),
            "raw":[int(v) for v in vals]
        })
    return result

def parse_canvases(data: bytes, tilelists):
    off=find_header(data,b"PLUGIN_CANVASLST")
    base=off+16
    count=u32(data,base)
    ptrs=[u32(data,base+4+i*4) for i in range(count)]
    canvases=[]
    for ci,cp in enumerate(ptrs):
        if data[cp-16:cp] != b"PLUGIN_CANVAS___":
            raise ValueError(f"canvas {ci}: invalid marker at 0x{cp:x}")
        meta0_ptr=u32(data,cp)
        meta0=[u32(data,meta0_ptr+i*4) for i in range(7)]
        packed=meta0[4]
        screens_x=packed & 0xffff
        screens_y=(packed >> 16) & 0xffff
        width=screens_x*40
        height=screens_y*30
        cell_count=width*height
        tilelist_idx=meta0[5]
        if tilelist_idx >= len(tilelists):
            raise ValueError(f"canvas {ci}: tilelist index {tilelist_idx} out of range")
        layer_count=u32(data,cp+16)
        layers=[]
        for li in range(layer_count):
            lp=u32(data,cp+20+li*4)
            if data[lp-16:lp] != b"PCANVAS_LAYER___":
                raise ValueError(f"canvas {ci} layer {li}: invalid marker")
            grid_ptr=u32(data,lp+12)
            cells=list(struct.unpack_from("<%dI" % cell_count,data,grid_ptr))
            layers.append({
                "index":li,
                "ptr":lp,
                "grid_ptr":grid_ptr,
                "gadgets":parse_gadgets(data,lp,grid_ptr),
                "cells":cells
            })
        canvases.append({
            "index":ci,
            "ptr":cp,
            "screens_x":screens_x,"screens_y":screens_y,
            "tiles_w":width,"tiles_h":height,
            "pixel_w":width*16,"pixel_h":height*16,
            "tilelist_index":tilelist_idx,
            "background_argb":meta0[6],
            "layers":layers
        })
    return canvases

def render_canvas(data,walls,tilelists,canvas,out_png: Path):
    tl=tilelists[canvas["tilelist_index"]]
    sheet=extract_wall(data,walls,tl["wall_id"])
    bg=canvas["background_argb"]
    rgb=((bg>>16)&255,(bg>>8)&255,bg&255,255)
    out=Image.new("RGBA",(canvas["pixel_w"],canvas["pixel_h"]),rgb)
    for layer in canvas["layers"]:
        for idx,code in enumerate(layer["cells"]):
            if code == 0:
                continue
            tx=code & 0xffff
            ty=(code >> 16) & 0xffff
            # Codes outside this tileset's logical grid are extension/special
            # codes. Keep them in IR; do not invent a visual mapping here.
            if tx >= tl["width"] or ty >= tl["height"]:
                continue
            tile=sheet.crop((tx*16,ty*16,tx*16+16,ty*16+16))
            x=(idx % canvas["tiles_w"])*16
            y=(idx // canvas["tiles_w"])*16
            out.alpha_composite(tile,(x,y))
    out.save(out_png,optimize=True)

def build_collision(data,tilelists,canvas,out_bin: Path):
    tl=tilelists[canvas["tilelist_index"]]
    n=canvas["tiles_w"]*canvas["tiles_h"]
    mask=bytearray(n)
    for layer in canvas["layers"]:
        for i,code in enumerate(layer["cells"]):
            flag=tile_attr(data,tl,code)
            # 0x20f is the full-solid ACTKOOL tile attribute observed in LAB.
            if flag == 0x20f:
                mask[i]=1
    out_bin.write_bytes(mask)
    return sum(mask)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("actbin",type=Path)
    ap.add_argument("out",type=Path)
    ap.add_argument("--preview-canvas",type=int,default=3)
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    data=args.actbin.read_bytes()
    walls=parse_wall_table(data)
    tilelists=parse_tilelists(data)
    canvases=parse_canvases(data,tilelists)

    # Full metadata IR; layer cells are compressed so all 109 maps remain practical.
    ir={"format":"LAB-ACTKOOL-SCENE-IR-v1","tile_size":16,
        "wall_count":len(walls),"tilelists":tilelists,"canvases":[]}
    total_gadgets=0
    for c in canvases:
        co={k:v for k,v in c.items() if k!="layers"}
        co["layers"]=[]
        for l in c["layers"]:
            total_gadgets += len(l["gadgets"])
            co["layers"].append({
                "index":l["index"],"ptr":l["ptr"],"grid_ptr":l["grid_ptr"],
                "gadgets":l["gadgets"],"cells":encode_cells(l["cells"])
            })
        ir["canvases"].append(co)
    ir["canvas_count"]=len(canvases)
    ir["gadget_placement_count"]=total_gadgets
    (args.out/"scene-ir.json").write_text(json.dumps(ir,separators=(",",":")),encoding="utf-8")

    ci=args.preview_canvas
    canvas=canvases[ci]
    render_canvas(data,walls,tilelists,canvas,args.out/f"canvas_{ci:03d}.png")
    solid=build_collision(data,tilelists,canvas,args.out/f"canvas_{ci:03d}_collision.bin")
    preview={
        "canvas":ci,
        "screens":[canvas["screens_x"],canvas["screens_y"]],
        "tiles":[canvas["tiles_w"],canvas["tiles_h"]],
        "pixels":[canvas["pixel_w"],canvas["pixel_h"]],
        "tilelist_index":canvas["tilelist_index"],
        "wall_id":tilelists[canvas["tilelist_index"]]["wall_id"],
        "gadgets":sum(len(x["gadgets"]) for x in canvas["layers"]),
        "solid_tiles":solid,
    }
    (args.out/f"canvas_{ci:03d}_meta.json").write_text(json.dumps(preview,indent=2),encoding="utf-8")
    print(json.dumps({
        "canvas_count":len(canvases),
        "tilelist_count":len(tilelists),
        "gadget_placements":total_gadgets,
        "preview":preview
    },indent=2))

if __name__=="__main__":
    main()
