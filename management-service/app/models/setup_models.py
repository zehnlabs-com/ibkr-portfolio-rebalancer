"""
Data models for setup endpoints
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator

class NotificationConfig(BaseModel):
    """Notification configuration for an account"""
    channel: str = Field(..., description="Strategy channel name (lowercase, hyphen-separated)")

class RebalancingConfig(BaseModel):
    """Rebalancing configuration for an account"""
    cash_reserve_percent: float = Field(default=1.0, ge=0.0, le=100.0, description="Cash reserve percentage")

class AccountConfig(BaseModel):
    """Configuration for a single account"""
    account_id: str = Field(..., description="IBKR account ID (e.g., U123456 or DU123456)")
    type: str = Field(default="paper", description="Account type: 'live' or 'paper'")
    replacement_set: Optional[str] = Field(None, description="ETF replacement set name (e.g., 'ira')")
    notification: NotificationConfig
    rebalancing: RebalancingConfig
    
    @validator('account_id')
    def validate_account_id(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError('account_id must be a non-empty string')
        v = v.strip()
        if not (v.startswith('U') or v.startswith('DU')):
            raise ValueError('account_id must start with "U" (live) or "DU" (paper)')
        return v
    
    @validator('type', always=True)
    def validate_type(cls, v, values):
        # Auto-set type based on account_id
        account_id = values.get('account_id', '')
        if account_id.startswith('DU'):
            return 'paper'
        elif account_id.startswith('U'):
            return 'live'
        return v

class ReplacementRule(BaseModel):
    """ETF replacement rule"""
    source: str = Field(..., description="Source ETF symbol")
    target: str = Field(..., description="Target ETF symbol")
    scale: float = Field(default=1.0, ge=0.0, description="Scale factor for replacement")

class AccountsData(BaseModel):
    """Complete accounts configuration data"""
    accounts: List[AccountConfig]
    replacement_sets: Optional[Dict[str, List[ReplacementRule]]] = Field(default_factory=dict)

class SaveAccountsRequest(BaseModel):
    """Request model for saving accounts"""
    accounts: List[AccountConfig]

class SaveAccountsResponse(BaseModel):
    """Response model for saving accounts"""
    message: str

class AccountsDataResponse(BaseModel):
    """Response model for getting accounts data"""
    accounts: List[Dict[str, Any]]
    replacement_sets: Dict[str, Any]

class SaveEnvRequest(BaseModel):
    """Request model for saving environment variables"""
    env_content: str = Field(..., description="Complete .env file content")

class SaveEnvResponse(BaseModel):
    """Response model for saving environment variables"""
    message: str

class EnvDataResponse(BaseModel):
    """Response model for getting environment data"""
    env_content: str

class SetupStatusResponse(BaseModel):
    """Response model for setup status"""
    env_exists: bool
    accounts_exists: bool

class CompleteSetupResponse(BaseModel):
    """Response model for completing setup"""
    status: str
    message: str