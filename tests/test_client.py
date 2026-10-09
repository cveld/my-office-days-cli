import json

import httpx
import respx
import pytest

from my_office_days.client import ModApiError, ModClient


@respx.mock
def test_get_uses_employee_session_verbatim():
    route = respx.get("https://api.example.test/me").mock(
        return_value=httpx.Response(200, json={"id": 42})
    )

    with ModClient("https://api.example.test", "secret") as client:
        assert client.get("/me") == {"id": 42}

    assert route.calls[0].request.headers["authorization"] == "secret"


@respx.mock
def test_graphql_uses_app_batch_envelope():
    route = respx.post("https://tenant.server.example/connection/graphql").mock(
        return_value=httpx.Response(
            200, json={"buildings": {"data": {"buildings": []}}}
        )
    )

    with ModClient("https://tenant.server.example", "session") as client:
        assert client.graphql("buildings", "query buildings { buildings { guid } }") == {
            "buildings": []
        }

    request = route.calls[0].request
    assert request.headers["authorization"] == "session"
    assert request.headers["content-type"].startswith("application/json")
    assert json.loads(request.content) == [
        {
            "name": "buildings",
            "query": "query buildings { buildings { guid } }",
            "variables": {},
        }
    ]


@respx.mock
def test_graphql_reports_server_error_without_leaking_headers():
    respx.post("https://tenant.server.example/connection/graphql").mock(
        return_value=httpx.Response(
            200, json={"bookings": {"errors": [{"message": "not allowed"}]}}
        )
    )

    with ModClient("https://tenant.server.example", "session-secret") as client:
        with pytest.raises(ModApiError, match="not allowed") as caught:
            client.graphql("bookings", "query bookings { bookings { guid } }")

    assert "session-secret" not in str(caught.value)


@respx.mock
def test_login_uses_confirmed_form_endpoints_without_authorization():
    reset = respx.post(
        "https://tenant.server.example/customer/connection/rest/employee/reset"
    ).mock(return_value=httpx.Response(200, json={"status": "success"}))
    authenticate = respx.post(
        "https://tenant.server.example/customer/connection/rest/employee/authenticate"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "success",
                "guid": "employee-1",
                "authorisation": "session-secret",
                "key": "encryption-secret",
            },
        )
    )

    with ModClient("https://tenant.server.example/customer") as client:
        client.request_login_token("person@example.test")
        result = client.authenticate("person@example.test", "123456")

    assert result["guid"] == "employee-1"
    assert "authorization" not in reset.calls[0].request.headers
    assert reset.calls[0].request.headers["content-type"].startswith(
        "application/x-www-form-urlencoded"
    )
    assert reset.calls[0].request.content == (
        b"email=person%40example.test&forceEmail=false&accessTo=app"
    )
    assert authenticate.calls[0].request.content == (
        b"email=person%40example.test&token=123456"
    )


@respx.mock
def test_login_rejects_application_error_without_leaking_response_data():
    respx.post("https://tenant.server.example/connection/rest/employee/authenticate").mock(
        return_value=httpx.Response(
            200,
            json={"status": "error", "error": "invalid_token", "token": "secret"},
        )
    )

    with ModClient("https://tenant.server.example") as client:
        with pytest.raises(ModApiError, match="invalid_token") as caught:
            client.authenticate("person@example.test", "123456")

    assert "secret" not in str(caught.value)
