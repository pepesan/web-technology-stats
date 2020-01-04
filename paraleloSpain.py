import threading
from launchSpain import recorreSitio
from gestionaDatos import SiteSpain

def thread_function(sitio):
    #logging.info("Thread %s: starting", sitio)
    recorreSitio(sitio)
    #logging.info("Thread %s: finishing", sitio)

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    #logging.basicConfig(format=format, level=logging.INFO,datefmt="%H:%M:%S")
    for index in range(20000):
        sites = SiteSpain.objects[:100](finished=False, retries__lte=1)
        #sites = Site.objects[:100](finished=False, retries__exists=True, retries__lte=5)
        threads = list()
        for sitio in sites:
            #logging.info("Main    : create and start thread %d.", sitio)
            x = threading.Thread(target=recorreSitio, args=(sitio,))
            threads.append(x)
            x.start()
        for index, thread in enumerate(threads):
            #logging.info("Main    : before joining thread %d.", index)
            thread.join()
            #logging.info("Main    : thread %d done", index)
