import csv
from gestionaDatos import *


def leeFicheroYGuarda(fichero):
    listado_sitios = []
    with open(fichero) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        print("Leyendo fichero...")
        for row in csv_reader:
            # print(f'\t{row[0]} works in the {row[1]} department, and was born in {row[2]}.')
            listado_sitios.append({'id': row[0], 'url': row[1]})
            sitio = Site()
            sitio.position = row[0]
            sitio.url = row[1]
            sitio.finished = False
            sitio.last_search_datetime = datetime.today()
            sitio.batch = BATCH
            sitio.retries = 0
            try:
                sitio.save()
                print("Sitio Guardado: " + row[1])
            except Exception as e:
                # print("Error al guardar sitio: " + row[1])
                p = 1
                # print (e)
            line_count += 1
            if line_count % 1000 == 0:
                print("Linea: " + str(line_count))
        print(f'Líneas {line_count} procesadas.')
    return listado_sitios


# fichero = 'top-1m.csv'
fichero = '2019-top-1m.csv'
listado = leeFicheroYGuarda(fichero)
# for elemento in listado:
#    print(elemento)
