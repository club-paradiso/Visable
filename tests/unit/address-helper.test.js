/* Address Helper unit tests — ported from club-paradiso/jusoyuno
   (tests/address.test.js + tests/ocr.test.js) when JUSOYUNO was folded into
   Visable as a tool. The Azure handwriting tests are not ported: that feature
   stays out of Visable. Run: node --test tests/unit/address-helper.test.js */
const test=require("node:test");
const assert=require("node:assert/strict");
const handler=require("../../api/address/search.js");
const statusHandler=require("../../api/address/status.js");
const DEFAULT={keyword:"제주시 중앙로 1"};

let ipCounter=0;
function harness(method="POST",body=DEFAULT,headers={}){
  let status=200,response,headersOut={};
  // Unique synthetic client IP per harness so the per-IP rate limiter
  // never leaks state between tests; rate-limit tests pass an explicit IP.
  const merged={"x-forwarded-for":`198.51.100.${++ipCounter%250}`,...headers};
  return {
    req:{method,body,headers:merged},
    res:{
      setHeader(key,value){headersOut[key]=value;},
      status(code){status=code;return this;},
      json(data){response=data;return this;}
    },
    output(){return {status,response,headers:headersOut};}
  };
}
async function inKeyContext(key,upstream,run){
  const originalKey=process.env.JUSO_API_KEY,originalFetch=global.fetch;
  if(key===null)delete process.env.JUSO_API_KEY;else process.env.JUSO_API_KEY=key;
  if(upstream)global.fetch=upstream;
  try{await run();}finally{
    if(originalKey===undefined)delete process.env.JUSO_API_KEY;
    else process.env.JUSO_API_KEY=originalKey;
    global.fetch=originalFetch;
  }
}
const fakeResponse=(code="0",items=[],totalCount)=>({ok:true,json:async()=>({results:{common:{errorCode:code,...(totalCount!==undefined?{totalCount:String(totalCount)}:{})},juso:items}})});

test("rejects GET, invalid bodies, oversized payloads and non-JSON media",async()=>{
  const calls=[
    harness("GET"),harness("POST",{}),harness("POST",{keyword:"1"}),
    harness("POST",{keyword:"x".repeat(81)}),
    harness("POST",{keyword:"<script>"}),
    harness("POST",{keyword:"010-1234-5678"}),
    harness("POST",{keyword:"private@example.org"}),
    harness("POST",{keyword:"900101-1234567"}),
    harness("POST",{keyword:"1234567890"}),
    harness("POST",DEFAULT,{"content-type":"text/plain"}),
    harness("POST",DEFAULT,{"content-length":"9000"})
  ];
  const codes=[405,400,400,400,400,400,400,400,400,415,413];
  for(let i=0;i<calls.length;i++){
    await handler(calls[i].req,calls[i].res);
    assert.equal(calls[i].output().status,codes[i]);
  }
});
test("missing key fails closed and readiness check never reveals a key",async()=>{
  await inKeyContext(null,null,async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().status,503);
    assert.equal(x.output().response.code,"NOT_CONFIGURED");
    const health=harness("GET");await statusHandler(health.req,health.res);
    assert.equal(health.output().response.configured,false);
    assert.equal("key" in health.output().response,false);
  });
});
test("correct URL, form request and Korean/English address field mapping",async()=>{
  await inKeyContext("dev-example-key",async(url,options)=>{
    assert.equal(url,"https://business.juso.go.kr/addrlink/addrLinkApi.do");
    assert.equal(options.method,"POST");
    assert.equal(new URLSearchParams(options.body).get("confmKey"),"dev-example-key");
    assert.equal(new URLSearchParams(options.body).get("keyword"),DEFAULT.keyword);
    assert.equal(new URLSearchParams(options.body).get("resultType"),"json");
    return fakeResponse("0",[{roadAddrPart1:"제주특별자치도 제주시 중앙로 1",engAddr:"1, Jungang-ro, Jeju-si, Jeju-do",zipNo:"63166",jibunAddr:"제주시 이도일동",bdNm:"건물"}]);
  },async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().status,200);
    assert.deepEqual(x.output().response.results[0],{
      roadAddr:"제주특별자치도 제주시 중앙로 1",
      roadAddrPart2:"",
      engAddr:"1, Jungang-ro, Jeju-si, Jeju-do",
      jibunAddr:"제주시 이도일동",
      zipNo:"63166",
      buildingName:"건물"
    });
    assert.equal(x.output().response.verifiedBaseOnly,true);
  });
});
test("full official roadAddr (incl. reference item) is preferred over roadAddrPart1",async()=>{
  await inKeyContext("key",async()=>fakeResponse("0",[{
    roadAddr:"제주특별자치도 제주시 중앙로 1 (이도일동)",
    roadAddrPart1:"제주특별자치도 제주시 중앙로 1",
    roadAddrPart2:"(이도일동)",
    engAddr:"1, Jungang-ro, Jeju-si, Jeju-do",zipNo:"63166",jibunAddr:"제주시 이도일동",bdNm:""
  }],1),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().status,200);
    assert.equal(x.output().response.results[0].roadAddr,"제주특별자치도 제주시 중앙로 1 (이도일동)");
    assert.equal(x.output().response.results[0].roadAddrPart2,"(이도일동)");
    assert.equal(x.output().response.totalCount,1);
  });
});
test("multiple matches are preserved and capped at 8",async()=>{
  const items=Array.from({length:10},(_,i)=>({
    roadAddrPart1:`서울특별시 강남구 테헤란로 ${i+1}`,
    engAddr:`${i+1}, Teheran-ro, Gangnam-gu, Seoul`,zipNo:"06100",jibunAddr:"역삼동",bdNm:i===0?"센터필드":""
  }));
  await inKeyContext("key",async()=>fakeResponse("0",items,10),async()=>{
    const x=harness("POST",{keyword:"서울특별시 강남구 테헤란로"});await handler(x.req,x.res);
    assert.equal(x.output().status,200);
    assert.equal(x.output().response.results.length,8);
    assert.equal(x.output().response.totalCount,10);
    assert.equal(x.output().response.results[0].buildingName,"센터필드");
  });
});
test("unicode/Korean keyword is forwarded to the official API intact",async()=>{
  const keyword="서울특별시 강남구 테헤란로 231";
  await inKeyContext("key",async(url,options)=>{
    assert.equal(new URLSearchParams(options.body).get("keyword"),keyword);
    return fakeResponse("0",[]);
  },async()=>{
    const x=harness("POST",{keyword});await handler(x.req,x.res);
    assert.equal(x.output().status,200);
  });
});
test("empty official search response is valid, not fabricated",async()=>{
  await inKeyContext("key",async()=>fakeResponse("0",[]),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().status,200);assert.deepEqual(x.output().response.results,[]);
  });
});
test("wrong key, expired key, rejected query and provider outages differ",async()=>{
  for(const [apiCode,expectedHttp,expectedCode] of [
    ["E0001",503,"JUSO_AUTH_FAILED"],["E0002",503,"JUSO_AUTH_FAILED"],["E0014",503,"JUSO_AUTH_FAILED"],
    ["E0006",422,"JUSO_QUERY_REJECTED"],["E0015",422,"JUSO_QUERY_REJECTED"],
    ["-999",502,"UPSTREAM_UNAVAILABLE"]
  ]){
    await inKeyContext("key",async()=>fakeResponse(apiCode),async()=>{
      const x=harness();await handler(x.req,x.res);
      assert.equal(x.output().status,expectedHttp);
      assert.equal(x.output().response.code,expectedCode);
    });
  }
  await inKeyContext("key",async()=>({ok:true,json:async()=>{throw new Error("bad json")}}),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().response.code,"UPSTREAM_BAD_RESPONSE");
  });
});
test("upstream HTTP error and malformed payload map to 502 codes",async()=>{
  await inKeyContext("key",async()=>({ok:false,status:500,json:async()=>({})}),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().status,502);
    assert.equal(x.output().response.code,"UPSTREAM_UNAVAILABLE");
  });
  await inKeyContext("key",async()=>({ok:true,json:async()=>({unexpected:true})}),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(x.output().status,502);
    assert.equal(x.output().response.code,"UPSTREAM_BAD_RESPONSE");
  });
});
test("upstream timeout maps to 504 UPSTREAM_TIMEOUT",async()=>{
  for(const name of ["TimeoutError","AbortError"]){
    await inKeyContext("key",async()=>{const e=new Error("timed out");e.name=name;throw e;},async()=>{
      const x=harness();await handler(x.req,x.res);
      assert.equal(x.output().status,504);
      assert.equal(x.output().response.code,"UPSTREAM_TIMEOUT");
    });
  }
});
test("API key value never appears in any response body",async()=>{
  const secret="super-secret-test-value-123";
  await inKeyContext(secret,async()=>fakeResponse("0",[{roadAddrPart1:"제주시 중앙로 1",engAddr:"1, Jungang-ro",zipNo:"63166",jibunAddr:"이도일동",bdNm:""}]),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(JSON.stringify(x.output().response).includes(secret),false);
    const health=harness("GET");await statusHandler(health.req,health.res);
    assert.equal(health.output().response.configured,true);
    assert.equal(JSON.stringify(health.output().response).includes(secret),false);
  });
  await inKeyContext(secret,async()=>fakeResponse("E0001"),async()=>{
    const x=harness();await handler(x.req,x.res);
    assert.equal(JSON.stringify(x.output().response).includes(secret),false);
  });
});
test("status endpoint rejects non-GET methods",async()=>{
  const x=harness("POST");await statusHandler(x.req,x.res);
  assert.equal(x.output().status,405);
});
test("per-client rate limit returns 429 RATE_LIMITED after 30 requests/minute",async()=>{
  handler._resetRateLimit();
  const ip={"x-forwarded-for":"203.0.113.77"};
  await inKeyContext(null,null,async()=>{
    let last;
    for(let i=0;i<31;i++){last=harness("POST",DEFAULT,ip);await handler(last.req,last.res);}
    assert.equal(last.output().status,429);
    assert.equal(last.output().response.code,"RATE_LIMITED");
    assert.equal(last.output().headers["Retry-After"],"60");
    // A different client is unaffected.
    const other=harness();await handler(other.req,other.res);
    assert.equal(other.output().status,503);
  });
  handler._resetRateLimit();
});
test("no key or entered identity number ever leaves the browser/server as lookup request",async()=>{
  await inKeyContext(null,()=>{throw new Error("Should not call upstream");},async()=>{
    const x=harness("POST",{keyword:"900101-1234567"});
    await handler(x.req,x.res);assert.equal(x.output().response.code,"SENSITIVE_QUERY");
  });
});

const core=require("../../assets/js/address-ocr-core.js");
test("OCR normalization preserves Korean number and letters",()=>{
 assert.equal(core.normalizeText(" 제주특별자치도  제주시\t중앙로 1 \r\n 101동  "), "제주특별자치도 제주시 중앙로 1 \n 101동");
});
test("Candidate ranking prefers actual address, not a name or lease price",()=>{
 const out=core.extractCandidates([
  {text:"성명 김철수\n보증금 20000000원\n제주특별자치도 제주시 중앙로 1",confidence:73,source:"original"},
  {text:"제주특별자치도 제주시 중앙로 1",confidence:89,source:"contrast"},
  {text:"Phone 010-1234-5678",confidence:98,source:"binary"}
 ]);
 assert.equal(out[0].text,"제주특별자치도 제주시 중앙로 1");
 assert.ok(!out.some(x=>x.text.includes("010-")));
});
test("No made-up address generated when OCR fails",()=>{
 assert.deepEqual(core.extractCandidates([{text:"손글씨를 판독할 수 없습니다",confidence:5}]),[]);
 assert.equal(core.confidenceHint([]),"none");
});
test("Handwriting-like multi-line candidate joins address tokens only",()=>{
 const got=core.extractCandidates([{text:"제주특별자치도 제주시\n중앙로 1",confidence:42}]);
 assert.ok(got.some(x=>x.text==="제주특별자치도 제주시 중앙로 1"));
});
test("Pixel preprocessing transforms grayscale, keeps sizes and alpha",()=>{
 const source=new Uint8ClampedArray([250,250,250,255,12,14,18,255,150,90,90,255,230,230,230,255]);
 for(const mode of ["grayscale","contrast","binary","sharpen"]){
   const result=core.enhancePixels(source,2,2,mode);
   assert.equal(result.length,16);assert.equal(result[3],255);assert.equal(result[7],255);
   assert.equal(result[0],result[1]);assert.equal(result[1],result[2]);
 }
 assert.throws(()=>core.enhancePixels(source,0,2,"binary"));
});
test("Low confidence handwriting cannot be presented as verified",()=>{
 assert.equal(core.confidenceHint([{text:"제주시 중앙로 1",score:61,confidence:43}]),"low");
 assert.equal(core.confidenceHint([{text:"제주시 중앙로 1",score:96,confidence:95}]),"medium");
});
test("sharpen enhancement preserves pixel shape and edge quality diagnostics",()=>{
 const pixels=new Uint8ClampedArray(12*12*4);
 for(let y=0;y<12;y++)for(let x=0;x<12;x++){const k=(y*12+x)*4,ink=(x%4===0||y%4===0)?0:255;pixels.set([ink,ink,ink,255],k);}
 const sharper=core.enhancePixels(pixels,12,12,"sharpen");
 assert.equal(sharper.length,pixels.length);
 const metric=core.imageQuality(pixels,12,12);
 assert.ok(metric.edgeScore>8);
 assert.equal(metric.likelyBlurry,false);
 const blank=new Uint8ClampedArray(12*12*4).fill(255);
 const blankQuality=core.imageQuality(blank,12,12);
 assert.equal(blankQuality.likelyBlurry,true);
});
test("a clear printed road address stops after one OCR pass",()=>{
 // Receipt text as read by Tesseract kor on the first (original) pass.
 const clear=core.extractCandidates([{text:"6(;(070-7017-0404)\n세주 제주시 노연로 7 (노형통)\n",confidence:83,source:"original"}]);
 assert.equal(core.isConfidentRead(clear),true);
 const faint=core.extractCandidates([{text:"세주 세수시 도열로 7 (노형동)\n",confidence:56,source:"original"}]);
 assert.equal(core.isConfidentRead(faint),false);
 assert.equal(core.isConfidentRead(core.extractCandidates([{text:"제주시 노형동 925",confidence:90}])),false);
 assert.equal(core.isConfidentRead([]),false);
});
test("address queries tolerate a misread word by narrowing to city + road + number",()=>{
 assert.deepEqual(core.addressQueries("세수 제주시 노연로 7 (노형통"),["제주시 노연로 7","노연로 7","세수 제주시 노연로 7"]);
 assert.deepEqual(core.addressQueries("부산 해운대구 구남로 3번길 5"),["해운대구 구남로 3번길 5","구남로 3번길 5","부산 해운대구 구남로 3번길 5"]);
 assert.deepEqual(core.addressQueries("세수시 도열로 7 (노형동) -"),["세수시 도열로 7","도열로 7"]);
 // Lot-number (jibun) addresses have no road to narrow to.
 assert.deepEqual(core.addressQueries("제주시 노형동 925"),["제주시 노형동 925"]);
});
