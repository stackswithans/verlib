from verlib.call import HttpHeaders


def test_http_headers_makes_key_case_insensitive():
    headers = HttpHeaders(
        {"Content-type": "application/json", "Content-Length": 68}
    )

    assert "cOntent-Type" in headers
    assert "content-Type" in headers
    assert "CONTENT-TYPE" in headers
    assert "content-length" in headers
    assert "Content-lengTh" in headers
    assert "CONTENT-LENGTH" in headers
    assert "CONTENT-LENGTH1" not in headers

    assert headers["CONTENT-TYPE"] == "application/json"
    assert headers["CONTENT-Length"] == 68
    assert headers.get("CONTENT-TYPE") == "application/json"
    assert headers.get("content-LENGTH") == 68
    assert headers.get("content-LENGTH1") is None
