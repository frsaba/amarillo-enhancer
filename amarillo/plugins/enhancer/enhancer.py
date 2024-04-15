import logging
import logging.config

from amarillo.plugins.enhancer.configuration import configure_enhancer_services
from amarillo.utils.container import container
from amarillo.models.Carpool import Carpool

from amarillo.services.hooks import CarpoolEvents, register_carpool_event_listener
logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger("enhancer")
class EnhancerCarpoolEvents(CarpoolEvents):
    def on_create(carpool: Carpool):
        container['carpools'].put(carpool.agency, carpool.id, carpool)
    def on_update(carpool: Carpool):
        container['carpools'].put(carpool.agency, carpool.id, carpool)
    def on_delete(carpool: Carpool):
        container['carpools'].delete(carpool.agency, carpool.id)

def setup(app):
    logger.info("Hello Enhancer")

    configure_enhancer_services()
    register_carpool_event_listener(EnhancerCarpoolEvents)