from datetime import timedelta

DOMAIN = "seltron_clausius"
PLATFORMS = ("sensor", "binary_sensor", "number", "select", "datetime", "switch")

CONF_POLLING_INTERVAL = "polling_interval"
DEFAULT_POLLING_INTERVAL = 300
POLLING_INTERVAL_OPTIONS = {
    30: "30 s",
    60: "1 min",
    120: "2 min",
    180: "3 min",
    240: "4 min",
    300: "5 min",
    600: "10 min",
    900: "15 min",
    1200: "20 min",
    1500: "25 min",
    1800: "30 min",
    3600: "60 min",
}
POLLING_INTERVALS = tuple(POLLING_INTERVAL_OPTIONS)
UPDATE_INTERVAL = timedelta(seconds=DEFAULT_POLLING_INTERVAL)


def polling_interval_seconds(value: object) -> int:
    """Return a supported polling interval or the safe default."""
    if type(value) is int and value in POLLING_INTERVALS:
        return value
    return DEFAULT_POLLING_INTERVAL

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"
