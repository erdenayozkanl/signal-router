from router.core import CircuitBreaker,SlidingWindowRateLimiter,RouterMetrics,generate,invoke_with_fallback,route

def test_pii_stays_local():
    choice=route('Email me at alice@example.com',allow_cloud=True,prefer_local=False)
    assert choice.model.startswith('local') and choice.pii_detected

def test_complex_request_large():
    choice=route('Analyze the tradeoffs between event-driven architecture and batch processing')
    assert choice.model=='local-large'

def test_cost_fallback():
    choice=route('Analyze distributed systems',allow_cloud=True,prefer_local=False,max_cost_usd=0)
    assert choice.model=='local-large'

def test_simulation_is_explicit():
    result=generate('hello',route('hello'),simulate=True)
    assert result['output'] is None and result['provider']=='simulation'

def test_breaker():
    t=[0]
    b=CircuitBreaker(threshold=2,cooldown=5,clock=lambda:t[0])
    b.record(False);b.record(False)
    assert not b.allow()
    t[0]=6
    assert b.allow()

def test_limiter_and_fallback():
    clock=[0]; limiter=SlidingWindowRateLimiter(1,10,lambda:clock[0])
    assert limiter.allow() and not limiter.allow()
    primary,fallback=route('hello'),route('analyze system design')
    metrics=RouterMetrics()
    def invoke(_, choice):
        if choice is primary: raise OSError('primary down')
        return {'ok':True}
    result=invoke_with_fallback('x',primary,fallback,CircuitBreaker(),invoke,metrics)
    assert result['fallback_used'] and metrics.snapshot()['calls']==1
