"""
Scenarios API Routes
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.services.scenarios import (
    get_scenario, 
    list_scenarios, 
    get_default_scenario,
    SCENARIOS
)

router = APIRouter(prefix="/scenarios")


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: Optional[str] = None


class ScenarioDetailResponse(ScenarioResponse):
    context: str
    ambiance: Optional[str] = None


class ScenarioListResponse(BaseModel):
    scenarios: List[ScenarioResponse]
    total: int


@router.get("", response_model=ScenarioListResponse)
async def list_all_scenarios(include_spicy: bool = True):
    """List available scenarios"""
    scenarios = list_scenarios(include_spicy=include_spicy)
    return ScenarioListResponse(
        scenarios=[ScenarioResponse(**s) for s in scenarios],
        total=len(scenarios)
    )


@router.get("/{scenario_id}", response_model=ScenarioDetailResponse)
async def get_scenario_detail(scenario_id: str):
    """Get scenario details"""
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioDetailResponse(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        icon=scenario.icon,
        context=scenario.context,
        ambiance=scenario.ambiance
    )


@router.get("/character/{character_id}/default")
async def get_character_default_scenario(character_id: str):
    """Get default scenario for a character"""
    scenario_id = get_default_scenario(character_id)
    scenario = get_scenario(scenario_id)
    if not scenario:
        scenario = get_scenario("neutral")
    return {
        "character_id": character_id,
        "scenario_id": scenario.id,
        "scenario_name": scenario.name
    }
