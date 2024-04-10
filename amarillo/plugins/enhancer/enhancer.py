import json
from multiprocessing import Process, current_process
import logging
import logging.config
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import psutil
from setproctitle import setproctitle

from amarillo.plugins.enhancer.configuration import configure_enhancer_services
from amarillo.utils.container import container
from amarillo.models.Carpool import Carpool
from amarillo.utils.utils import agency_carpool_ids_from_filename

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
logger = logging.getLogger("enhancer")

class EventHandler(FileSystemEventHandler):
    # TODO FG HB should watch for both carpools and agencies
    # in data/agency, data/agencyconf, see AgencyConfService

    def on_closed(self, event):
  
        logger.info("CLOSE_WRITE: Created %s", event.src_path)
        try:
            with open(event.src_path, 'r', encoding='utf-8') as f:
                dict = json.load(f)
                carpool = Carpool(**dict)

            container['carpools'].put(carpool.agency, carpool.id, carpool)
        except FileNotFoundError as e:
            logger.error("Carpool could not be added, as already deleted (%s)", event.src_path)
        except:
            logger.exception("Eventhandler on_closed encountered exception")        

    def on_deleted(self, event):
        try:
            logger.info("DELETE: Removing %s", event.src_path)
            (agency_id, carpool_id) = agency_carpool_ids_from_filename(event.src_path)
            container['carpools'].delete(agency_id, carpool_id)
        except:
            logger.exception("Eventhandler on_deleted encountered exception")


def run_enhancer():
    setproctitle("amarillo-enhancer")

    # check if another enhancer process is already running, if it is then exit
    this_proc = psutil.Process(os.getpid())

    for proc in psutil.process_iter():
        try:
            # Check if process name is enhancer and we share a grandparent with it (parent should be the uvicorn worker)
            # Keep the enhancer process with lowest pid
            if this_proc.pid > proc.pid and "amarillo-enhancer" in proc.name() and this_proc.parents()[1].pid == proc.parents()[1].pid :
                logger.info("Enhancer already running")
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.error(e)

    logger.info("Hello Enhancer")

    configure_enhancer_services()

    observer = Observer()  # Watch Manager

    observer.schedule(EventHandler(), 'data/carpool', recursive=True)
    observer.start()

    import time

    try:
        # TODO FG Is this really needed?
        cnt = 0
        ENHANCER_LOG_INTERVAL_IN_S = 600
        while True:
            if cnt == ENHANCER_LOG_INTERVAL_IN_S:
                logger.debug("Currently stored carpool ids: %s", container['carpools'].get_all_ids())
                cnt = 0

            time.sleep(1)
            cnt += 1
    finally:
        observer.stop()
        observer.join()

        logger.info("Goodbye Enhancer")

def setup(app):        
    process = Process(name="amarillo-enhancer", target=run_enhancer)
    process.daemon = True
    process.start()


if __name__ == "__main__":
    run_enhancer()