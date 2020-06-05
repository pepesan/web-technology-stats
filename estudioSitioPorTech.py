from gestionaDatos import *
import os
import plotly.graph_objects as go

REPORTDIR = 'report'

resultados = Site.objects[:50].order_by('position')(finished=True)

def print_resultados(resultados):
    for resultado in resultados:
        print(resultado)

print_resultados(resultados)

alltechs = Site.objects.order_by('position')(finished=True, position__gte=20).distinct("tech")[:50]
print_resultados(alltechs)
for tech in alltechs:
    nTech = Tech(name=tech)
    try:
        nTech.save()
        print("Tech Guardada: " + tech)
        sitios_con_tech = Site.objects.order_by('position')(tech=tech, finished=True, position__gte=20)[:20]
        print("Sitios con Tech")
        print_resultados(sitios_con_tech)

        for sitio in sitios_con_tech:
            print(sitio)

            for teche in sitio.tech:
                print(teche)
                print(nTech)
                exit()
                if(teche!=tech):
                    if(len(nTech.related_tech)>0):
                        if (nTech.related_tech[teche]!=None):
                            nTech.related_tech[teche] += 1
                        else:
                            nTech.related_tech[teche] = 1
                print(nTech)
    except Exception as e:
        print("Error al guardar tech: " + str(tech))
        print (e)













