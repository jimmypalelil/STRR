"""Expected (method, rule) pairs for STRR API routes (excludes Flasgger/Swagger UI).

Update this frozenset when registering new blueprints or routes in ``strr_api``.
"""

# Generated from Flask ``app.url_map`` (HEAD/OPTIONS omitted); excludes flasgger/static.
EXPECTED_STRR_API_ROUTES = frozenset(
    {
        ("GET", "/accounts/"),
        ("POST", "/accounts/"),
        ("GET", "/accounts/search"),
        ("POST", "/address/<path:action>"),
        ("GET", "/applications"),
        ("POST", "/applications"),
        ("DELETE", "/applications/<application_number>"),
        ("GET", "/applications/<application_number>"),
        ("PUT", "/applications/<application_number>/assign"),
        ("GET", "/applications/<application_number>/auto-approval-records"),
        ("POST", "/applications/<application_number>/decision/set-aside"),
        ("POST", "/applications/<application_number>/documents"),
        ("PUT", "/applications/<application_number>/documents"),
        ("DELETE", "/applications/<application_number>/documents/<file_key>"),
        ("GET", "/applications/<application_number>/documents/<file_key>"),
        ("GET", "/applications/<application_number>/events"),
        ("GET", "/applications/<application_number>/host/related-registrations"),
        ("GET", "/applications/<application_number>/ltsa"),
        ("POST", "/applications/<application_number>/notice-of-consideration"),
        ("PUT", "/applications/<application_number>/payment-details"),
        ("GET", "/applications/<application_number>/payment/receipt"),
        ("PUT", "/applications/<application_number>/status"),
        ("PATCH", "/applications/<application_number>/str-address"),
        ("PUT", "/applications/<application_number>/unassign"),
        ("POST", "/applications/<string:application_number>"),
        ("PUT", "/applications/<string:application_number>"),
        ("GET", "/applications/search"),
        ("GET", "/applications/user/search"),
        ("POST", "/documents"),
        ("DELETE", "/documents/<file_key>"),
        ("GET", "/meta/info"),
        ("GET", "/ops/healthz"),
        ("GET", "/ops/readyz"),
        ("POST", "/permits/<path:action>"),
        ("GET", "/registrations"),
        ("GET", "/registrations/<registration_id>"),
        ("PUT", "/registrations/<registration_id>/assign"),
        ("POST", "/registrations/<registration_id>/decision/set-aside"),
        ("POST", "/registrations/<registration_id>/documents"),
        ("GET", "/registrations/<registration_id>/documents/<file_key>"),
        ("GET", "/registrations/<registration_id>/events"),
        ("POST", "/registrations/<registration_id>/notice-of-consideration"),
        ("GET", "/registrations/<registration_id>/snapshots/<snapshot_id>"),
        ("PUT", "/registrations/<registration_id>/status"),
        ("PATCH", "/registrations/<registration_id>/str-address"),
        ("GET", "/registrations/<registration_id>/todos"),
        ("PUT", "/registrations/<registration_id>/unassign"),
        ("PUT", "/registrations/<registration_number>/expiry"),
        ("GET", "/registrations/<registration_number>/validate"),
        ("POST", "/registrations/permit-validation-registration"),
        ("GET", "/registrations/search"),
        ("GET", "/registrations/user/search"),
        ("POST", "/users/"),
        ("GET", "/users/tos"),
        ("PATCH", "/users/tos"),
        ("POST", "/v1/address/<path:action>"),
        ("POST", "/v1/permits/<path:action>"),
    }
)

# Routes that do not require JWT (public).
PUBLIC_ROUTES = frozenset(
    {
        ("GET", "/ops/healthz"),
        ("GET", "/ops/readyz"),
        ("GET", "/meta/info"),
    }
)
