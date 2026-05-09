from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RuntimeHealthState(str, Enum):
    healthy = "healthy"
    warning = "warning"
    blocked = "blocked"


class AnalysisRuntimeProfile(BaseModel):
    llm_provider: str
    deep_think_llm: str
    quick_think_llm: str
    backend_url: str | None = None
    data_vendors: dict[str, str] = Field(default_factory=dict)
    vendor_fallback_policy: str = "explicit_multi_vendor_only"
    api_keys_present: dict[str, bool] = Field(default_factory=dict)


class RuntimeModelOption(BaseModel):
    label: str
    value: str


class RuntimeProviderCatalog(BaseModel):
    provider: str
    backend_url: str | None = None
    api_key_env: str | None = None
    quick_models: list[RuntimeModelOption] = Field(default_factory=list)
    deep_models: list[RuntimeModelOption] = Field(default_factory=list)


class RuntimeDataVendorCategory(BaseModel):
    category: str
    label: str
    current_vendor: str
    options: list[str] = Field(default_factory=list)


class AnalysisRuntimeCatalog(BaseModel):
    providers: dict[str, RuntimeProviderCatalog] = Field(default_factory=dict)
    data_vendor_categories: list[RuntimeDataVendorCategory] = Field(default_factory=list)
    known_data_vendors: list[str] = Field(default_factory=list)
    vendor_fallback_policy: str = "explicit_multi_vendor_only"


class RuntimeHealthCheck(BaseModel):
    component: str
    state: RuntimeHealthState
    configured: bool
    healthy: bool
    message: str
    recommended_action: str | None = None


class AnalysisRuntimeHealth(BaseModel):
    profile: AnalysisRuntimeProfile
    llm: RuntimeHealthCheck
    market_data: RuntimeHealthCheck


class WorkflowPreflight(BaseModel):
    workflow: str
    ready: bool
    state: RuntimeHealthState
    checks: list[RuntimeHealthCheck] = Field(default_factory=list)
    blocker_count: int = 0
    warning_count: int = 0


class PlatformPreflightSummary(BaseModel):
    analysis: WorkflowPreflight
    paper_manual: WorkflowPreflight
    paper_auto: WorkflowPreflight
