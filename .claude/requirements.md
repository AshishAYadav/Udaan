Create an Airline Booking and Servicing Management system

Description: 

The techstack should be FastAPI monolith server which has react UI library for fronend (after completing backend)

the FastAPI should have apis for 

1. getUsers - provides user information and tiers of membership such as gold bronze silver 
2. bookings - getbookings, makebookings
3. routes - getvalidflightroutes, getsourceairportslist, getdestinationslist
4. ssrs - createssr, deletessr, listssr
5. flights - searchflight/getflightschedules, createflightschedule, modifyflightschedule
6. classes - getavailablecabincalsses
7. fare - getfaresforflight, getfareforssr
8. passengers - getpassengers, addpassensgers, deletepassengers, modifypassengers
9. payments - createpayment, updatepayment, completepayment, getpaymentstatus
10. tickets - createtickets, deletetickets 
11. airports - getairportlist
12. chcekins - getcheckins, validatecheckin, createcheckin, updatecheckin
13. tiers - gettierslevelsinfo

Use TinyDB for database

the Database should have collections such as

{
    "bookings": [],
    "users": [],
    "routes": [],
    "specialservicerequests": [],
    "aircrafts": [], 
    "flights": [], //schedules - create a future of 2 months flightschedules 5 flights per day
    "classes": [],
    "fares": [],
    "passengers": [],
    "payments": [],
    "tickets": [],
    "airports": [],
    "checkins": [],
    "tier": []
}

follow airline conventions but not strictly, like a booking needs a valid flightschedule and seatavailability, a valid payment status (hardcode flow with approve or reject options),  and passengers, consider infant, child adult passenger classes.

a change booking flow - user change flights before 24hrs of depature only to a 7 days maximum future flight 

a pnr is created with bookings but ticket is generated only when checkin is completed

flights - a schedule shall list flights available from database and which is not associated with another flight in last or next 48 hrs

specialservices requests shall be created based on tiers, eligibility, like meal option addition, lounge addition, wheelchair additon, bassinet addition, excess baggage, create necessary db collections as required

This is not production but a prototype sandbox environment for flight management system

add necessary apis required 

create a swagger api documentation also

UI 

A simple react ui where user can search the flights using origin destinations and date, and select any flight and add passenger info (no ancillary addition or baggage addition needed here anything just pure booking then it can be implemented later to add it or use apis to do it manually) - do payment get pnr

view pnr ui can be resued in checkin flow

a checkin flow - user shall be able to enter pnr/lastname details to checkin by confirming  and get a printable ticket or boaridng pass

an admin ui to add flights and list flights in tablse format

keep ui sleek simple light theme, not much css needed a simple bootstrap css looking ui is also good, but use tailwind


