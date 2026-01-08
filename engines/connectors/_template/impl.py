from pydantic import BaseModel
from engines.common.identity import RequestContext

class SampleInput(BaseModel):
    param: str

async def handle_sample(ctx: RequestContext, args: SampleInput):
    return {"status": "ok", "received": args.param}
