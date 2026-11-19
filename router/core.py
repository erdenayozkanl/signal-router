"""Explainable policy-based LLM request router, with budgets and circuit breakers."""
import json
import os
import re
import time
import urllib.request
from collections import deque
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class Route:
    model: str
    reason: str
    estimated_cost_usd: float
    complexity: str
    pii_detected: bool

# Illustrative pricing only. These are internal simulation coefficients, not vendor quotes.
COST_PER_1K = {'local-small':0.0, 'local-large':0.0, 'cloud-small':0.001, 'cloud-large':0.01}

def detect_pii(prompt: str) -> bool:
    return bool(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\+?\d[\d\s()-]{9,}\d\b',prompt))

def complexity(prompt: str) -> str:
    indicators=('analyze','design','architecture','tradeoff','compare','debug','proof','reason','evaluate',
                'analiz','tasarla','karşılaştır','mimari','değerlendir')
    return 'high' if len(prompt.split())>60 or any(word in prompt.lower() for word in indicators) else 'low'

def route(prompt: str, allow_cloud=False, max_cost_usd=0.01, prefer_local=True) -> Route:
    if not prompt.strip(): raise ValueError('prompt cannot be empty')
    is_pii=detect_pii(prompt)
    level=complexity(prompt)
    estimated_tokens=max(1,len(prompt)//4)+500
    cloud_model='cloud-large' if level=='high' else 'cloud-small'
    estimated_cost=round(estimated_tokens/1000*COST_PER_1K[cloud_model],6)
    if is_pii:
        return Route('local-large' if level=='high' else 'local-small','PII policy: keep request local',0,level,True)
    if not allow_cloud or prefer_local:
        return Route('local-large' if level=='high' else 'local-small','Local-first or cloud not allowed',0,level,False)
    if estimated_cost>max_cost_usd:
        return Route('local-large' if level=='high' else 'local-small','Estimated cloud cost exceeds budget',0,level,False)
    return Route(cloud_model,'Cloud enabled and cost within illustrative budget',estimated_cost,level,False)

class CircuitBreaker:
    def __init__(self, threshold=3, cooldown=30, clock=time.monotonic):
        self.threshold=threshold;self.cooldown=cooldown;self.clock=clock
        self.failures=0;self.opened=None
    def allow(self):
        return self.opened is None or self.clock()-self.opened>=self.cooldown
    def record(self, ok):
        if ok:
            self.failures=0;self.opened=None
        else:
            self.failures+=1
            if self.failures>=self.threshold: self.opened=self.clock()

class SlidingWindowRateLimiter:
    """In-process limiter; use a shared store for multi-instance deployments."""
    def __init__(self, limit=60, window_seconds=60, clock=time.monotonic): self.limit,self.window,self.clock,self.events=limit,window_seconds,clock,deque()
    def allow(self):
        now=self.clock()
        while self.events and now-self.events[0]>=self.window: self.events.popleft()
        if len(self.events)>=self.limit: return False
        self.events.append(now); return True

class RouterMetrics:
    def __init__(self): self.calls=[]
    def record(self, route_name, elapsed_ms, ok): self.calls.append({'route':route_name,'latency_ms':round(elapsed_ms,2),'ok':ok})
    def snapshot(self):
        values=sorted(x['latency_ms'] for x in self.calls)
        def p(n): return values[min(len(values)-1,int((len(values)-1)*n))] if values else 0
        return {'calls':len(values),'p50_ms':p(.5),'p95_ms':p(.95),'errors':sum(not x['ok'] for x in self.calls)}

def invoke_with_fallback(prompt, primary, fallback, breaker, invoke, metrics=None):
    started=time.monotonic()
    for choice in (primary,fallback):
        if choice is None or (choice is primary and not breaker.allow()): continue
        try:
            result=invoke(prompt,choice); breaker.record(True)
            if metrics: metrics.record(choice.model,(time.monotonic()-started)*1000,True)
            return {**result,'selected_model':choice.model,'fallback_used':choice is fallback}
        except Exception: breaker.record(False)
    if metrics: metrics.record(primary.model,(time.monotonic()-started)*1000,False)
    raise RuntimeError('all configured providers failed')

def generate(prompt: str, selected: Route, simulate=False) -> dict:
    if simulate:
        return {'provider':'simulation','model':selected.model,'output':None,
                'message':'Policy-only dry run: no LLM inference performed'}
    if selected.model.startswith('cloud'):
        raise RuntimeError('Cloud provider deliberately not configured: use --simulate or local policy')
    name=os.getenv('OLLAMA_LARGE_MODEL','llama3.1:8b') if selected.model=='local-large' else os.getenv('OLLAMA_SMALL_MODEL','llama3.2:3b')
    req=urllib.request.Request(os.getenv('OLLAMA_URL','http://localhost:11434')+'/api/generate',
         data=json.dumps({'model':name,'prompt':prompt,'stream':False}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as response:
        data=json.load(response)
    return {'provider':'ollama','model':name,'output':data['response']}
