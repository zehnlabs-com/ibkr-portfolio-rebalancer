from pydantic import BaseModel, Field
from typing import Optional

class RebalanceRequest(BaseModel):
    execution_mode: str = Field(default="dry_run", description="Execution mode: 'rebalance' for live execution, 'dry_run' for simulation")
    
    class Config:
        schema_extra = {
            "example": {
                "execution_mode": "dry_run"
            }
        }