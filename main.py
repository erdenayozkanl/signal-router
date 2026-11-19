import argparse
import json
from dataclasses import asdict
from router.core import generate,route

def main():
    p=argparse.ArgumentParser(description='SignalRouter: local-first model selection')
    p.add_argument('prompt',nargs='?',default='Explain caching')
    p.add_argument('--simulate',action='store_true', help='Policy test with NO LLM inference')
    p.add_argument('--cloud',action='store_true',help='Allow cloud routing (no cloud provider configured)')
    p.add_argument('--prefer-cloud',action='store_true')
    p.add_argument('--max-cost',type=float,default=0.01)
    p.add_argument('--serve',action='store_true')
    args=p.parse_args()
    if args.serve:
        import uvicorn
        uvicorn.run('api:app',host='127.0.0.1',port=8003)
    else:
        selected=route(args.prompt,args.cloud,args.max_cost,not args.prefer_cloud)
        print(json.dumps({'decision':asdict(selected),'generation':generate(args.prompt,selected,args.simulate)},indent=2))
if __name__=='__main__':main()
