"""
Support for Molobot.

For more details about this component, please refer to the documentation at
https://github.com/haoctopus/molobot
"""

from homeassistant.const import (EVENT_HOMEASSISTANT_START,
                                 EVENT_HOMEASSISTANT_STOP, EVENT_STATE_CHANGED,)

from .molo_client_config import MOLO_CONFIGS
from .molo_client_app import MOLO_CLIENT_APP
from .utils import LOGGER
import time

DOMAIN = 'molobot'
SERVICE_NAME = 'force_update'
NOTIFYID = 'molobotnotifyid'
VERSION = 101
is_init = False
last_start_time = time.time()


def setup(hass, config):
    """Set up molobot component."""
    LOGGER.info("Begin setup molobot!")


    # Load config mode from configuration.yaml.
    cfg = config[DOMAIN]
    cfg.update({"__version__": VERSION})

    if 'mode' in cfg:
        MOLO_CONFIGS.load(cfg['mode'])
    else:
        MOLO_CONFIGS.load('release')

    if 'http' in config and 'server_host' in config['http']:
        tmp_host = config['http']['server_host']
        MOLO_CONFIGS.get_config_object()['ha']['host'] = tmp_host
    if 'http' in config and 'server_port' in config['http']:
        tmp_port = config['http']['server_port']
        MOLO_CONFIGS.get_config_object()['ha']['port'] = tmp_port

    MOLO_CONFIGS.get_config_object()["hassconfig"] = cfg

    async def stop_molobot(event):
        """Stop Molobot while closing ha."""
        LOGGER.info("Begin stop molobot!")
        from .molo_bot_main import stop_aligenie
        stop_aligenie()

    async def start_molobot(event):
        """Start Molobot while starting ha."""
        LOGGER.debug("molobot started!")
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_molobot)
        last_start_time = time.time()



    async def hass_started(event):
        global is_init
        is_init = True

    async def on_state_changed(event):
        """Disable the dismiss button."""
        global is_init
        global last_start_time

        if MOLO_CLIENT_APP.molo_client:
            if is_init :
                MOLO_CLIENT_APP.molo_client.sync_device(True, 2)
                is_init = False
            elif last_start_time and (time.time() - last_start_time > 30):
                last_start_time = None
                MOLO_CLIENT_APP.molo_client.sync_device(True, 2)
            elif not is_init or not last_start_time:
                new_state = event.data.get("new_state")
                if not new_state:
                    return

                entity_id = event.data.get("entity_id") or new_state.entity_id
                domain = _get_domain(entity_id)

                if domain == 'switch':
                    # notify to tmall
                    state = {
                        'entity_id': entity_id,
                        'state': new_state.state,
                        'domain': domain

                    }
                    LOGGER.error(state)
                    MOLO_CLIENT_APP.molo_client.sync_device_state(state)
                else:
                    MOLO_CLIENT_APP.molo_client.sync_device(False, 60)

    def _get_domain(entity_id):
        return entity_id.split(".")[0]


    def force_update(call):
        """Handle the service call."""
        MOLO_CLIENT_APP.molo_client.sync_device(True, 2, force_diff=True)
        hass.states.set("%s_service.%s" % (DOMAIN, SERVICE_NAME) , 'update time: %s' % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    hass.services.register(DOMAIN, SERVICE_NAME, force_update)

    from .molo_bot_main import run_aligenie
    run_aligenie(hass)

    if not cfg.get("disablenotify", False):
        hass.components.persistent_notification.async_create(
            "Welcome to molobot!", "Molo Bot Infomation", "molo_bot_notify")

    hass.bus.async_listen_once('homeassistant_started', hass_started)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_molobot)
    hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed)


    return True


