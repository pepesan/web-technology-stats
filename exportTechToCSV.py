import csv
from gestionaDatos import *

tech="WordPress"
with open("report/" + tech + '.csv', mode='w') as tech_file:
    tech_writer = csv.writer(tech_file, delimiter=':', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    sitios = Site.objects.order_by('position')(finished=True, tech__exists=True, tech=tech)
    tech_writer.writerow(["url", "position", "tech_list"])
    lines = 0
    for sitio in sitios:
        techString = ",".join(sitio.tech)
        tech_writer.writerow([sitio.url, str(int(sitio.position)), techString])
        lines += 1
    print("Lineas: " + str(lines))