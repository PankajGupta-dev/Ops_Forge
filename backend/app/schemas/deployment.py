from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class PlannerRequest(BaseModel):
    description: str = Field(..., description="User deployment intent (e.g. 'Deploy with PostgreSQL and autoscaling')")
    dockerfile: str = Field(..., description="Raw Dockerfile content")
    repository: Optional[str] = Field(None, description="Selected GitHub repository (owner/repo)")
    branch: Optional[str] = Field(None, description="Selected Git branch")

class ApplicationSpec(BaseModel):
    name: str = Field(..., description="Application or service identifier")
    runtime: str = Field(..., description="Inferred runtime environment (e.g., python, node, go)")
    base_image: Optional[str] = Field(None, description="Container base image")
    language: Optional[str] = Field(None, description="Programming language")
    framework: Optional[str] = Field(None, description="Web framework if identified")
    working_dir: Optional[str] = Field(None, description="Container working directory")
    exposed_ports: List[int] = Field(default_factory=list, description="Ports exposed by container")
    entry_command: Optional[List[str]] = Field(None, description="Entry command / CMD elements")

class DeploymentConfig(BaseModel):
    platform: str = Field(default="railway", description="Target cloud deployment platform")
    region: str = Field(default="nyc3", description="Target deployment region slug")
    strategy: str = Field(default="rolling", description="Deployment strategy (rolling, canary, blue-green)")
    replicas: int = Field(default=1, ge=1, description="Desired instance replica count")

class ResourceLimits(BaseModel):
    cpu: str = Field(default="500m", description="CPU request/limit string (e.g. 500m, 1vcpu)")
    ram: str = Field(default="1Gi", description="RAM allocation string (e.g. 512Mi, 1Gi)")
    instance_size: str = Field(default="basic-xs", description="Cloud provider instance size slug")

class AutoscalingConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether autoscaling is enabled")
    min_instances: int = Field(default=1, ge=1, description="Minimum instance count")
    max_instances: int = Field(default=3, ge=1, description="Maximum instance count")
    target_cpu_utilization: Optional[int] = Field(default=80, ge=1, le=100, description="Target CPU utilization percentage")

class DatabaseConfig(BaseModel):
    required: bool = Field(default=False, description="Whether database provisioning is required")
    engine: Optional[str] = Field(None, description="Database engine (postgresql, mongodb, mysql, redis)")
    version: Optional[str] = Field(None, description="Engine version")
    size: Optional[str] = Field(None, description="Instance size slug for managed database")

class NetworkConfig(BaseModel):
    ports: List[int] = Field(default_factory=lambda: [8080], description="Publicly routed HTTP/HTTPS container ports")
    public_http: bool = Field(default=True, description="Whether application exposes public HTTP endpoint")
    custom_domain: Optional[str] = Field(None, description="Optional custom domain binding")

class HealthCheckConfig(BaseModel):
    path: str = Field(default="/healthz", description="HTTP health check path")
    port: int = Field(default=8080, description="Health check target port")
    initial_delay_seconds: int = Field(default=10, ge=0, description="Initial delay before health probing")
    period_seconds: int = Field(default=15, ge=1, description="Health check frequency interval")
    timeout_seconds: int = Field(default=5, ge=1, description="Health check request timeout")

class DeploymentPlan(BaseModel):
    application: ApplicationSpec = Field(..., description="Application component metadata")
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig, description="Deployment orchestration parameters")
    resources: ResourceLimits = Field(default_factory=ResourceLimits, description="Hardware resource constraints")
    autoscaling: AutoscalingConfig = Field(default_factory=AutoscalingConfig, description="Autoscaling policy")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Managed database requirements")
    network: NetworkConfig = Field(default_factory=NetworkConfig, description="Networking and routing specification")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variable key-value pairs")
    healthcheck: HealthCheckConfig = Field(default_factory=HealthCheckConfig, description="Health check configuration")
    warnings: List[str] = Field(default_factory=list, description="Warnings or potential configuration alerts")
    assumptions: List[str] = Field(default_factory=list, description="Explicit assumptions made by Gemini during reasoning")

class DeploymentResult(BaseModel):
    trace_id: Optional[str] = Field(None, description="Globally unique trace identifier for workflow lineage tracking")
    status: str = Field(..., description="Deployment outcome status (e.g., 'success', 'failed', 'building', 'active')")
    app_id: Optional[str] = Field(None, description="Provisioned application ID")
    deployment_id: Optional[str] = Field(None, description="Active deployment run ID")
    app_name: Optional[str] = Field(None, description="Human-readable application name")
    live_url: Optional[str] = Field(None, description="Public application endpoint URL")
    message: str = Field(..., description="Summary or status message")
    created_at: Optional[str] = Field(None, description="UTC ISO-8601 creation timestamp")
    build_duration: Optional[float] = Field(None, description="Container image build duration in seconds")
    deployment_duration: Optional[float] = Field(None, description="Railway service deployment duration in seconds")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional deployment metadata")

    @property
    def deployment_status(self) -> str:
        return self.status

    @property
    def deployment_url(self) -> Optional[str]:
        return self.live_url

class DeployRequest(BaseModel):
    description: str = Field(..., description="User deployment intent")
    dockerfile: str = Field(..., description="Raw Dockerfile content")
    repository: Optional[str] = Field(None, description="Selected GitHub repository (owner/repo)")
    branch: Optional[str] = Field(None, description="Selected Git branch")

