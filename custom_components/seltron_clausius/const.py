from datetime import timedelta

DOMAIN = "seltron_clausius"
PLATFORMS = ("sensor", "binary_sensor", "number", "select", "datetime", "switch")
UPDATE_INTERVAL = timedelta(minutes=5)

CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"
