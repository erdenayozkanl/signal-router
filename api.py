from dataclasses import asdict
from fastapi import FastAPI
from pydantic import BaseModel
from router.core import route, generate
app=FastAPI(title='SignalRouter')
class Request(BaseModel):
    prompt: str
    simulate: bool = True
    allow_cloud: bool = False
    prefer_local: bool = True
    max_cost_usd: float = 0.01
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/route')
def decide(r:Request):
    decision=route(r.prompt,r.allow_cloud,r.max_cost_usd,r.prefer_local)
    return {'decision':asdict(decision),'generation':generate(r.prompt,decision,r.simulate)}
