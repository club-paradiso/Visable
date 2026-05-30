import olefile, zlib, struct, sys, re

EXT = {1,2,3,4,5,6,7,8,9,11,12,14,15,16,17,18,21,22,23}  # 8-wchar inline controls

def para_text(payload):
    # payload is bytes of HWPTAG_PARA_TEXT: array of UTF-16LE WCHARs with inline controls
    n=len(payload)//2
    arr=struct.unpack_from('<%dH'%n, payload, 0)
    out=[]; i=0
    while i<n:
        c=arr[i]
        if c in EXT:
            i+=8  # skip the 8-wchar extended control region
            continue
        if c==10:  # line break
            out.append('\n'); i+=1; continue
        if c==13:  # para break
            out.append('\n'); i+=1; continue
        if c<32:
            i+=1; continue
        out.append(chr(c)); i+=1
    return ''.join(out)

def extract(path, outpath):
    ole=olefile.OleFileIO(path)
    compressed=True
    try:
        fh=ole.openstream('FileHeader').read()
        compressed=bool(struct.unpack_from('<I',fh,36)[0] & 1)
    except Exception: pass
    sects=[e for e in ole.listdir() if len(e)==2 and e[0]=='BodyText' and e[1].startswith('Section')]
    sects.sort(key=lambda e:int(re.search(r'(\d+)',e[1]).group(1)))
    paras=[]
    for e in sects:
        data=ole.openstream(e).read()
        if compressed:
            try: data=zlib.decompress(data,-15)
            except Exception: pass
        i=0; n=len(data)
        while i+4<=n:
            hdr=struct.unpack_from('<I',data,i)[0]; i+=4
            tag=hdr & 0x3ff; size=(hdr>>20)&0xfff
            if size==0xfff:
                size=struct.unpack_from('<I',data,i)[0]; i+=4
            if i+size>n: break
            payload=data[i:i+size]; i+=size
            if tag==67:  # HWPTAG_PARA_TEXT
                paras.append(para_text(payload))
    ole.close()
    full='\n'.join(paras)
    # collapse runs of spaces
    full=re.sub(r'[ \t]{2,}',' ',full)
    open(outpath,'w',encoding='utf-8').write(full)
    ko=sum(1 for ch in full if '가'<=ch<='힣')
    return len(full), ko, len(paras)

for nm,src in [('stay','docs/source-manuals/2026-05/stay_manual_2026_05_21.hwp'),
               ('visa','docs/source-manuals/2026-05/visa_manual_2026_05_21.hwp')]:
    L,K,P=extract(src, f'/tmp/manual_text/{nm}2.txt')
    print(f"{nm}: chars={L} korean={K} paras={P}")
