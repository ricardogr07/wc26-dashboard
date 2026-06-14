import azure.functions as func
from api.cors import cors_headers
from api.handlers.admin_override import handle_admin_override
from api.handlers.matches import handle_matches
from api.handlers.simulate import handle_simulate
from api.handlers.standings import handle_standings
from api.handlers.sync import handle_sync

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="{*path}", methods=["OPTIONS"])
def options_preflight(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(status_code=200, headers=cors_headers())


@app.route(route="health", methods=[func.HttpMethod.GET])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("ok", status_code=200)


@app.route(route="standings", methods=[func.HttpMethod.GET])
def standings(req: func.HttpRequest) -> func.HttpResponse:
    return handle_standings(req)


@app.route(route="matches", methods=[func.HttpMethod.GET])
def matches(req: func.HttpRequest) -> func.HttpResponse:
    return handle_matches(req)


@app.route(
    route="admin/override", methods=[func.HttpMethod.POST], auth_level=func.AuthLevel.FUNCTION
)
def admin_override(req: func.HttpRequest) -> func.HttpResponse:
    return handle_admin_override(req)


@app.route(route="simulate", methods=[func.HttpMethod.POST])
def simulate(req: func.HttpRequest) -> func.HttpResponse:
    return handle_simulate(req)


@app.timer_trigger(
    arg_name="timer",
    schedule="%TIMER_SCHEDULE%",
    run_on_startup=False,
)
def sync_matches(timer: func.TimerRequest) -> None:
    handle_sync(timer)
