from fastapi import APIRouter

from app.api.common import error_responses
from app.schemas.baggage import BaggagePolicyRow
from app.schemas.misc import PolicyDocument, PolicyDocumentSummary
from app.services import baggage_service, policy_service

router = APIRouter(tags=["Policies & help"])


@router.get("/policies", response_model=list[PolicyDocumentSummary], summary="List policy documents",
            description="Customer-facing policies (Markdown in docs/policies). Used by the Help page and suitable for RAG ingestion.")
def list_policies():
    return policy_service.list_policies()


@router.get("/policies/{slug}", response_model=PolicyDocument, responses=error_responses(404, auth=False),
            summary="Get a policy document")
def get_policy(slug: str):
    return policy_service.get_policy(slug)


@router.get("/baggage/allowances", response_model=list[BaggagePolicyRow], summary="Baggage allowance table",
            description="Standard allowance for every route type (DOMESTIC / INTERNATIONAL), cabin and passenger type. "
                        "Members add their tier's bonus kg to checked baggage.")
def baggage_allowances():
    return baggage_service.policy_table()
