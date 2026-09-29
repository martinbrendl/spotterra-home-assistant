"""Konstanty integrace Spotterra pro Home Assistant."""

DOMAIN = "spotterra"

DEFAULT_URL = "https://spotterra.com"

CONF_TOKEN = "token"
CONF_URL = "url"

# Server obnovuje stav zhruba každých 25 s a hlášení drží 15 minut.
# Častější dotaz by nepřinesl nic nového, řidší by hlásič zpožďoval
# víc, než letadlo stihne přeletět.
SCAN_INTERVAL_S = 30

# Událost na sběrnici HA — trigger pro blueprint hlásiče. Vedle entity
# `event.*`, protože šablony v blueprintu jsou nad `trigger.event.data`
# čitelnější než nad atributy entity.
BUS_UDALOST = "spotterra_udalost"

# Druhy událostí, které server posílá (tag push payloadu). `alert` je
# výchozí; cokoli dalšího přijde pod svým jménem.
DRUHY_UDALOSTI = ["alert", "hlidka"]
