from __future__ import annotations
import sys
from pathlib import Path
import pytest
from pydantic import TypeAdapter, ValidationError
from sitescore_commerce.contracts import ANALYSIS_REQUEST_ADAPTER
from conftest import valid_analysis
REPO_ROOT=Path(__file__).resolve().parents[2]; API_SRC=REPO_ROOT/"sitescore-api"/"src"
def _frozen_adapter():
    sys.path.insert(0,str(API_SRC))
    try:
        from sitescore_api.models import AnalysisRequest
        return TypeAdapter(AnalysisRequest)
    finally: sys.path.remove(str(API_SRC))
@pytest.mark.parametrize("sector",["coffee","restaurant","gym","beauty"])
def test_valid_sector_payloads_match_frozen_contract(sector):
    payload=valid_analysis(sector); assert ANALYSIS_REQUEST_ADAPTER.validate_python(payload).model_dump(mode="json")==_frozen_adapter().validate_python(payload).model_dump(mode="json")
@pytest.mark.parametrize("mutation",["unknown","wrong_country","missing_shape","bool_number"])
def test_invalid_payloads_rejected_by_both_contracts(mutation):
    payload=valid_analysis("coffee")
    if mutation=="unknown": payload["mystery"]=1
    elif mutation=="wrong_country": payload["location"]["country_code"]="GB"
    elif mutation=="missing_shape": payload["location"].pop("city"); payload["location"].pop("state")
    else: payload["business_inputs"]["target_population"]=True
    for adapter in [ANALYSIS_REQUEST_ADAPTER,_frozen_adapter()]:
        with pytest.raises(ValidationError): adapter.validate_python(payload)
