from property_service import PropertyService, SignupRequest


class FakeClient:
    def __init__(self):
        self.calls = []

    def call(self, method, path, body=None, query=None):
        self.calls.append((method, path, body))
        if path.endswith("captcha/verify"):
            return {"verified": True}
        if path.endswith("user/create"):
            return {"id": "user-17"}
        return {"session_id": "session-17"}


def test_signup_links_captcha_user_and_server_session():
    client = FakeClient()
    result = PropertyService(client).signup(SignupRequest("a@tenant.test", "pw", "A Tenant", "captcha", "widget-17"))
    assert result == {"user_id": "user-17", "session_id": "session-17"}
    assert [call[1] for call in client.calls] == [
        "/v1/captcha/verify", "/v1/auth/user/create", "/v1/auth/session/create"
    ]
    assert client.calls[-1][2]["user_id"] == "user-17"
    assert client.calls[0][2]["widget_record_id"] == "widget-17"
