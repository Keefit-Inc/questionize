"""One-process, crash-conservative budget leases for a private research study."""
import asyncio
import json
import uuid

from .eval_budget_cr import private_write


class StudyBudgetStop(RuntimeError): pass


class StudyBudget:
    def __init__(self,path,limit=30.):
        self.path,self.limit=path,limit;self.condition=asyncio.Condition()
        old=json.loads(path.read_text()) if path.exists() else {}
        if old and old['limit_usd']!=limit:raise ValueError('Do not silently change the study budget')
        # An interrupted in-flight request may have been billed: charge its full reservation.
        self.spent=old.get('charged_usd',0.)+sum(old.get('leases',{}).values())
        self.leases={};self.unknown=old.get('unknown_usage',0);self.save()

    def save(self):private_write(self.path,{'limit_usd':self.limit,'charged_usd':round(self.spent,9),'leases':self.leases,'unknown_usage':self.unknown})

    async def reserve(self,amount):
        async with self.condition:
            while self.spent+sum(self.leases.values())+amount>self.limit+1e-9:
                if not self.leases:raise StudyBudgetStop('Study token-price envelope exhausted')
                await self.condition.wait()
            token=uuid.uuid4().hex;self.leases[token]=amount;self.save();return token

    async def finish(self,token,metrics):
        async with self.condition:
            reserved=self.leases.pop(token)
            known=sum(c.get('normalised_usd',0.) for c in metrics)
            unknown=[c for c in metrics if c.get('generation_calls') and not c.get('usage_complete')]
            charge=known+sum(max(0,c.get('allowance_usd',0)-c.get('normalised_usd',0)) for c in unknown)
            if charge>reserved+.000001:raise ValueError('Item overran its reserved envelope')
            self.spent+=charge;self.unknown+=len(unknown);self.save();self.condition.notify_all()
