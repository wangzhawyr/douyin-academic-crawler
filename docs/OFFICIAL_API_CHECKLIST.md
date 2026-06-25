# Official API Checklist

Complete this checklist before implementing any `official_api` request.

Only official open-platform authorized APIs are permitted. Do not add private
web/App endpoints, reverse-engineered URLs, automatic login, captcha bypass,
rate-limit evasion, account-password handling, or simulated attacks.

## Application Information

- Official platform application name:
- Official client key:
- Official client secret file path:
- Registered redirect URI:
- Authorized account / organization:
- Data access purpose:

## Permission Information

- Approved permission package:
- Required scope list:
- Confirmed scope for comments: `video.comment`
- Approval status:
- Approval date:

## Token File Format

```json
{
  "access_token": "YOUR_ACCESS_TOKEN",
  "refresh_token": "YOUR_REFRESH_TOKEN",
  "expires_at": "YYYY-MM-DDTHH:MM:SS+08:00",
  "scopes": ["video.comment"]
}
```

Required fields: `access_token`, `refresh_token`, `expires_at`, `scopes`.

## Comment List API Confirmation

- Get comment list API URL:
- HTTP method:
- Request parameters:
- Return field mapping:
- Pagination fields:
- Error codes:
- Frequency limits:
- Whether child comments are supported:
- Whether only authorized account's own videos can be read:

## Implementation Gate

- [ ] API URL comes from official docs.
- [ ] No private web/App endpoint is used.
- [ ] Token file is local and gitignored.
- [ ] Scope includes `video.comment`.
- [ ] `max_depth<=1`.
- [ ] `max_pages<=1`.
- [ ] Audit fields are enabled.
- [ ] Request frequency follows official rate limits.
