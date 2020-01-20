from launchSpain import recorreSitio
from gestionaDatosSpain import SiteSpain
from mongoengine import *

def recorresitio_async(sitio):
    recorreSitio(sitio)




from multiprocessing import Process

if __name__ == "__main__":  # confirms that the code is under main function
    for index in range(1000):
        connected = False
        try:
            connect(host='127.0.0.1', port=27017, db='test', alias='default')
            connected = True
            # print("Conectado a la bbdd: "+sitio.url)
        except Exception as e:
            print("No se puede conectar a la BBDD por lo que se finaliza la ejecución")
            print("No olvides arrancar la BBDD MongoDB, antes de ejecutar los scripts")
            print("Motivo: " + str(e))


        sites = SiteSpain.objects.order_by('url')[:1000](finished=False, retries__lte=2)
        #disconnect(alias='default')

        procs = []

        # instantiating process with arguments
        for site in sites:
            # print(name)
            proc = Process(target=recorresitio_async, args=(site,))
            procs.append(proc)
            proc.start()

        # complete the processes
        #for proc in procs:
        #    proc.join()
        import time
        TIMEOUT = 10
        start = time.time()
        while time.time() - start <= TIMEOUT:
            if not any(p.is_alive() for p in procs):
                # All the processes are done, break now.
                break

            time.sleep(.1)  # Just to avoid hogging the CPU
        else:
            # We only enter this if we didn't 'break' above.
            print("timed out, killing all processes")
            for p in procs:
                p.terminate()
                p.join()



