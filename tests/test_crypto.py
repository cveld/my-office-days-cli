import json

import httpx
import respx

from my_office_days.client import ModClient
from my_office_days.crypto import ALGORITHM_ID, IV_SEPARATOR, decode_payload, encode_payload


KEY = "00112233445566778899aabbccddeeff"


def test_encrypted_payload_round_trip():
    plaintext = '[{"name":"buildings","variables":{}}]'
    encoded = encode_payload(plaintext, KEY)

    assert encoded.startswith(ALGORITHM_ID)
    assert IV_SEPARATOR in encoded
    assert decode_payload(encoded, KEY) == plaintext


@respx.mock
def test_graphql_uses_encrypted_transport_when_key_is_present():
    response_body = {"buildings": {"data": {"buildings": []}}}
    route = respx.post("https://tenant.example/customer/connection/graphql").mock(
        return_value=httpx.Response(
            200, json=encode_payload(json.dumps(response_body), KEY, response=True)
        )
    )

    with ModClient("https://tenant.example/customer", "session", KEY) as client:
        assert client.graphql("buildings", "query buildings { buildings { guid } }") == {
            "buildings": []
        }

    request = route.calls[0].request
    assert request.headers["authorization"] == "session"
    assert request.headers["algorithm"] == ALGORITHM_ID
    decoded = json.loads(decode_payload(request.content.decode(), KEY))
    assert decoded[0]["name"] == "buildings"
