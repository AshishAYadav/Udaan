from fastapi import APIRouter, Query, status
from fastapi.responses import HTMLResponse

from app.api.common import error_responses
from app.auth.dependencies import Principal, optional, require
from app.models.enums import TicketStatus
from app.schemas.ticket import BoardingPass, Ticket, TicketCreate
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])

LAST_NAME = Query(None, description="Passenger last name; required unless you own the booking or are an admin")


@router.get("", response_model=list[Ticket], responses=error_responses(), summary="List tickets (admin)",
            description="Tickets filtered by booking, PNR or status.")
def list_tickets(
    booking_id: str | None = None, pnr: str | None = None, status: TicketStatus | None = None,
    _: Principal = require("admin"),
):
    return ticket_service.list_tickets(booking_id, pnr, status)


@router.post("", response_model=Ticket, status_code=status.HTTP_201_CREATED, responses=error_responses(404, 409),
             summary="Issue a ticket (admin)",
             description="Issues a ticket for a check-in. Only allowed when the check-in is CHECKED_IN and no ticket "
                         "has been issued yet. Normally `POST /api/checkins` issues tickets automatically. Requires "
                         "`tickets:write`.")
def create_ticket(payload: TicketCreate, _: Principal = require("tickets:write")):
    return ticket_service.issue_ticket(payload.checkin_id)


@router.get("/{ticket_id}", response_model=BoardingPass, responses=error_responses(404),
            summary="Get ticket / boarding pass",
            description="**Booking flow step 9.** Boarding pass data: passenger, PNR, ticket number, flight, route, "
                        "date/time, cabin and seat.")
def get_ticket(ticket_id: str, last_name: str | None = LAST_NAME, actor: Principal | None = optional("bookings:read")):
    ticket_service.get_accessible_ticket(ticket_id, actor, last_name)
    return ticket_service.boarding_pass(ticket_id)


@router.get("/{ticket_id}/boarding-pass", response_class=HTMLResponse, responses=error_responses(404),
            summary="Printable boarding pass (HTML)", description="Browser-printable boarding pass page.")
def boarding_pass_html(ticket_id: str, last_name: str | None = LAST_NAME, actor: Principal | None = optional("bookings:read")):
    ticket_service.get_accessible_ticket(ticket_id, actor, last_name)
    return ticket_service.boarding_pass_html(ticket_id)


@router.delete("/{ticket_id}", response_model=Ticket, responses=error_responses(404, 409),
               summary="Delete (cancel) a ticket (admin)",
               description="Marks an ISSUED ticket CANCELLED; the record is kept. Requires `tickets:write`.")
def delete_ticket(ticket_id: str, _: Principal = require("tickets:write")):
    return ticket_service.cancel_ticket(ticket_id)
