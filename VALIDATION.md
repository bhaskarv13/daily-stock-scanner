# Validation and remaining setup

Prepared 31 October 2026.

- The scanner was run against saved 30 October 2026 NSE final data and two years
  of Yahoo histories. It screened 487 stocks from a 501-symbol constituent file,
  excluding 14 non-EQ/unavailable/short-history entries. It reproduced these
  five qualifying stocks: ATHERENERG, NAVINFLUOR, ZYDUSLIFE, COFORGE, DIVISLAB.
- The selected four upstream PKScreener functions were compared structurally
  with the pinned original source. Their logic is unchanged.
- The pinned requirements installed successfully in a separate clean Python
  3.12 environment without the full PKScreener dependency tree.
- Python source syntax and workflow YAML structure were checked.
- Telegram setup was checked with mocked responses: missing tokens fail clearly,
  ambiguous conversations are refused, and a unique private chat is selected.
  No real Telegram credentials were used or messages sent during these tests.
- The latest-data fetch was checked against NSE and Yahoo from this execution
  environment. This does not verify access from GitHub's cloud IP addresses.

Not yet verified: an actual run in YOUR GitHub account, real Telegram delivery,
GitHub scheduled triggers, and cache behaviour on GitHub. Your first manual setup
and scan runs are the required account-side verification. The package is ready
for setup, but has not been deployed in your account.

The historical sample CSV is an example, not today's recommendation. Rules have
not been backtested for profitability. No trading orders are placed.
