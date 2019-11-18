# Repositorio de ejemplo de cálculo de estadísticas de tecnologías web
El presente repositorio trata de facilitar una serie de herramientas a la hora de extraer datos de tecnologías utilizadas en las principales webs 
## DataSet
El dataset utilizado es el del millón de páginas principales de internet de alexa. Concretado en el fichero top-1m.csv
## Mongoengine
La biblioteca se encargará de la definición de los modelos de la BBDD para almacenar la información de los sitios web. Están definidos en el fichero gestionaDatos.py
## Import
El fichero import.py trata de importar en la bbdd mongodb una colección llamada site que registrará los sitios de internet disponibles por url
$ python3 import.py
## Wappalize
Versión propia de script de python3 de la biblioteca wappalize, con el concunto de reglas de clasificación y análisis de tecnologías. Definidas en el fichero data/apps.json
## Lanzamiento
En el script launch.py están las funcionalidades que se encargan de realizar las peticiones extracción de información y guardado en la bbdd
Nota(no olvides las dependencias del proyecto)
$ pip install -r requirements.txt 
## Paralelización
En el script paralelo.py está la división en hilos de ejecución de la llamada a la bbdd para obtener un subset de urls y su procesado
$ python3 paralelo.py
## Docker compose
Se ha dejado un fichero docker compose que debería facilitar el lanzamiento de un servidor mongodb
## Procedimiento
 * Primero se ejecuta el docker-compose:
 docker-compose up -d
 * Después instalamos las dependencias:
 pip install -r requirements.txt
 * Después ejecutamos el importador: python3 import.py
 * Por fin ejecutamos el scrapper: python3 paralelo.py
 
 ## Nota final
 Ojito, son script muy pesados que peuden tardar desde varias horas a varios días en ejecutarse
 