from pydantic import BaseModel
from engines.common.identity import RequestContext

class ComputeInput(BaseModel):
    value: int

async def handle_compute(ctx: RequestContext, args: ComputeInput):
    return {"result": args.value * 2}
