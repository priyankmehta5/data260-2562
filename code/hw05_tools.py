"""HW5 domain tools, retry experiments, offline tests, and agent loop."""
from __future__ import annotations
import json, random, time, urllib.request, concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AGENCIES=[{"id":1,"agency_code":"VTA","name":"Valley Transportation Authority","jurisdiction":"Santa Clara County"}]
INCIDENTS=[
 {"id":1,"incident_code":"INC-0001","title":"Signal delay","severity":2,"agency_id":1},
 {"id":2,"incident_code":"INC-0002","title":"Platform crowding","severity":3,"agency_id":1},
 {"id":3,"incident_code":"INC-0003","title":"Critical track obstruction","severity":5,"agency_id":1},
]
def envelope(ok,data=None,error=None):
    return {"ok":ok,"data":data if ok else None,"error":None if ok else error}
def search(query):
    if not isinstance(query,str) or not query.strip(): return envelope(False,error="query must be a non-empty string")
    q=query.lower().strip()
    return envelope(True,[x for x in INCIDENTS if q in x["title"].lower() or q in x["incident_code"].lower()])
def detail_lookup(incident_id):
    if not isinstance(incident_id,int) or isinstance(incident_id,bool) or incident_id<=0:
        return envelope(False,error="incident_id must be a positive integer")
    item=next((x for x in INCIDENTS if x["id"]==incident_id),None)
    return envelope(True,item) if item else envelope(False,error="incident not found")
def aggregate():
    return envelope(True,{"incident_count":len(INCIDENTS),"mean_severity":sum(x["severity"] for x in INCIDENTS)/len(INCIDENTS),"agency_count":len(AGENCIES)})
def execute_tool(name,inputs):
    try:
        if name=="search": result=search((inputs or {}).get("query") if isinstance(inputs,dict) else None)
        elif name=="detail":
            result=detail_lookup((inputs or {}).get("incident_id") if isinstance(inputs,dict) else None)
            if result["ok"] and result["data"]["severity"]>=5:
                return json.dumps(envelope(False,error="safety rule blocked critical-incident detail"))
        elif name=="aggregate":
            if inputs not in ({},None): return json.dumps(envelope(False,error="aggregate accepts no inputs"))
            result=aggregate()
        else: return json.dumps(envelope(False,error="unknown tool"))
        return json.dumps(result)
    except Exception as exc: return json.dumps(envelope(False,error=str(exc)))
def retry_call(fn,rate,rng,attempts=3,backoff=0.001,timeout_s=2.0):
    started=time.perf_counter()
    for attempt in range(1,attempts+1):
        try:
            if rng.random()<rate: raise TimeoutError("injected timeout")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                value=pool.submit(fn).result(timeout=timeout_s)
            return True,attempt,(time.perf_counter()-started)*1000,value
        except Exception as exc:
            if attempt==attempts: return False,attempt,(time.perf_counter()-started)*1000,str(exc)
            time.sleep(backoff*(2**(attempt-1)))
    return False,attempts,(time.perf_counter()-started)*1000,"retry exhausted"
def run_experiment(out=ROOT/"reports/hw05/raw"):
    out.mkdir(parents=True,exist_ok=True); records=[]
    for rate in (0.0,0.2,0.5):
        for call in range(50):
            rng=random.Random(262562+int(rate*100)+call)
            ok,attempt,latency,value=retry_call(lambda: {"ok":True},rate,rng)
            records.append({"rate":rate,"call":call+1,"success":ok,"attempts":attempt,"latency_ms":round(latency,4),"result":value})
    (out/"fault_injection.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    return records
class OllamaModel:
    def __init__(self,model="qwen3:1.7b",base_url="http://127.0.0.1:11434"):
        self.model=model; self.url=base_url.rstrip("/")+"/api/chat"
    def next_action(self,history):
        prompt=("Return only JSON with keys tool and inputs. Choose one tool: search, detail, aggregate. "
                "Use aggregate with empty inputs to finish. History: "+json.dumps(history))
        body=json.dumps({"model":self.model,"stream":False,"format":"json","messages":[{"role":"user","content":prompt}]}).encode()
        req=urllib.request.Request(self.url,data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=30) as response:
            payload=json.loads(response.read().decode())
        content=payload.get("message",{}).get("content","")
        action=json.loads(content); return {"tool":action["tool"],"inputs":action.get("inputs",{})}
class MockModel:
    def __init__(self,action=None): self.action=action or {"tool":"search","inputs":{"query":"signal"}}
    def next_action(self,history): return self.action
def run_agent(user_input,model=None,max_steps=4,log_path=ROOT/"reports/hw05/raw/agent_runs.jsonl"):
    model=model or MockModel()
    steps=[]; stop="max_steps"
    for turn in range(1,max_steps+1):
        action=model.next_action(steps)
        if action is None: stop="completed"; break
        result=json.loads(execute_tool(action.get("tool"),action.get("inputs",{})))
        steps.append({"turn":turn,"tool":action.get("tool"),"inputs":action.get("inputs",{}),"result":result})
        if result.get("ok") and action.get("tool")=="aggregate": stop="completed"; break
    record={"user_input":user_input,"steps":steps,"stop_reason":stop,"tool_call_count":len(steps)}
    log_path.parent.mkdir(parents=True,exist_ok=True)
    with log_path.open("a",encoding="utf-8") as f: f.write(json.dumps(record)+"\n")
    return record
def run_offline_scenarios(out=ROOT/"reports/hw05/raw"):
    out.mkdir(parents=True,exist_ok=True)
    models=[MockModel({"tool":"search","inputs":{"query":"signal"}}),MockModel({"tool":"detail","inputs":{"incident_id":3}}),MockModel({"tool":"missing","inputs":{}}),MockModel({"tool":"search","inputs":{"query":"signal"}})]
    results=[run_agent(f"scenario-{i+1}",m,2,out/"agent_runs.jsonl") for i,m in enumerate(models)]
    (out/"offline_agent_scenarios.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    return results
def run_local_scenarios(out=ROOT/"reports/hw05/raw",model_name="qwen3:1.7b"):
    out.mkdir(parents=True,exist_ok=True); results=[]
    model=OllamaModel(model_name)
    for i,prompt in enumerate(["Find signal incidents","Summarize transit totals","Look up incident 1","Find platform crowding"],1):
        try: results.append(run_agent(prompt,model,4,out/"agent_runs.jsonl"))
        except Exception as exc: results.append({"scenario":i,"user_input":prompt,"error":str(exc),"stop_reason":"unavailable"})
    (out/"ollama_scenarios.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    return results
def self_test():
    tests=[
      ("search valid",json.loads(execute_tool("search",{"query":"signal"}))["ok"]),
      ("search invalid",not json.loads(execute_tool("search",{"query":""}))["ok"]),
      ("detail valid",json.loads(execute_tool("detail",{"incident_id":1}))["ok"]),
      ("detail invalid",not json.loads(execute_tool("detail",{"incident_id":"x"}))["ok"]),
      ("aggregate valid",json.loads(execute_tool("aggregate",{}))["ok"]),
      ("aggregate invalid",not json.loads(execute_tool("aggregate",{"inputs":{"unexpected":True}}))["ok"]),
      ("safety blocked",not json.loads(execute_tool("detail",{"incident_id":3}))["ok"]),
      ("max steps",run_agent("loop",MockModel({"tool":"search","inputs":{"query":"signal"}}),2)["stop_reason"]=="max_steps"),
    ]
    for name,ok in tests: print(("PASS" if ok else "FAIL")+" "+name)
    print(f"{sum(ok for _,ok in tests)}/{len(tests)}")
    return all(ok for _,ok in tests)
if __name__=="__main__":
    run_experiment(); run_offline_scenarios(); raise SystemExit(0 if self_test() else 1)
