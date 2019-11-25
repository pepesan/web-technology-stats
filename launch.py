from gestionaDatos import *
from pprint import pprint
from wappalyze import Wappalyzer, WebPage


def searchURL(url):
    try:
        wappalyzer = Wappalyzer.latest()
        webpage = WebPage.new_from_url('https://' + url, verify=False)
        result = wappalyzer.analyze(webpage)
    except Exception as e:
        #pprint("Fallo en sitio: " + str(url))
        #print (e)
        try:
            wappalyzer = Wappalyzer.latest()
            webpage = WebPage.new_from_url('http://' + url)
            result = wappalyzer.analyze(webpage)
        except Exception as e:
            #pprint("Fallo en sitio: " + str(url))
            #print(e)
            try:
                wappalyzer = Wappalyzer.latest()
                webpage = WebPage.new_from_url('https://www.' + url)
                result = wappalyzer.analyze(webpage)
            except Exception as e:
                # pprint("Fallo en sitio: " + str(url))
                print(e)
                result = None
    return result


def rellenaSitio(url, results):
    if (results == None):
        return None
    site = Site()
    site.url = url
    for resultado in results:
        site.tech.append(resultado)
    site.finished = True
    site.last_search_datetime = datetime.today()
    site.finished = True
    return site


def insertaSitio(url, sitio):
    sitioGuardado = Site.objects().get(url=url)
    if (sitio == None):
        return None
    sitioGuardado.tech = sitio.tech
    sitioGuardado.finish = True
    sitioGuardado.retries += 1
    sitioGuardado.last_search_datetime = datetime.today()
    Site.objects(url=url).update(set__tech=sitioGuardado.tech, set__last_search_datetime=datetime.today(),
                                 set__finished=True, set__retries=sitioGuardado.retries)
    return sitio


def recorreSitios(sitios):
    #pprint(sitios)
    for sitio in sitios:
        resultados = searchURL(sitio.url)
        sitioObj = rellenaSitio(sitio.url, resultados)
        sitioObj = insertaSitio(sitio.url, sitioObj)
        if (sitioObj == None):
            print(sitio.url + " no actualizada por fallo")
        #else:
            #pprint("sitio actualizado: " + str(sitioObj))


def recorreSitio(sitio):
    #pprint(sitio)
    resultados = searchURL(sitio.url)
    sitioObj = rellenaSitio(sitio.url, resultados)
    sitioObj = insertaSitio(sitio.url, sitioObj)
    if (sitioObj == None):
        Site.objects(url=sitio.url).update(inc__retries=1)
        print(sitio.url + " no actualizada por fallo")
    else:
        pprint("sitio actualizado: " + str(sitioObj))
