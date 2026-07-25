from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

class RecoveryStatus(str, Enum):
    PENDING = "pending"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    REJECTED = "rejected"

class CamelBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True
    )

class RecoveryStep(CamelBaseModel):
    id: str = Field(..., description="Unique step identifier")
    order: int = Field(..., description="Order of step execution")
    title: str = Field(..., description="Title or summary of step")
    command: Optional[str] = Field(None, description="Simulated or actual shell command")
    verified: bool = Field(False, description="Whether the step has been completed and verified")
    status: str = Field("pending", description="Status of the step: pending, running, completed, failed")

class RecoveryAction(CamelBaseModel):
    id: str = Field(..., description="Unique action identifier")
    trace_id: Optional[str] = Field(None, description="Globally unique workflow trace identifier")
    app_id: Optional[str] = Field(None, description="Cloud application platform identifier")
    deployment_id: Optional[str] = Field(None, description="Specific deployment run identifier")
    incident_id: str = Field(..., description="Incident identifier")
    title: str = Field(..., description="Action title")
    description: str = Field(..., description="Action description")
    steps: List[RecoveryStep] = Field(default_factory=list, description="Orchestrated steps")
    risk_level: str = Field(..., description="Risk tier: low, medium, high")
    status: RecoveryStatus = Field(RecoveryStatus.PENDING, description="Action status")
    estimated_duration: str = Field(..., description="Estimated duration string")
    approved_by: Optional[str] = Field(None, description="Operator who approved")
    executed_at: Optional[str] = Field(None, description="Timestamp of execution")
    narrative: Optional[str] = Field(None, description="Voice narration script text")
    audio_url: Optional[str] = Field(None, description="Audio file download endpoint URL")
    incident_record_id: Optional[str] = Field(None, description="MongoDB Atlas incident record identifier from Agent 5 Knowledge Memory")


class RecoveryApprovalRequest(CamelBaseModel):
    approved: bool = Field(..., description="Approved if True, Rejected if False")
    approver: Optional[str] = Field("Operator", description="Identity of the approver")
    approval_mode: Optional[str] = Field("ui", description="Approval medium: ui or voice")
