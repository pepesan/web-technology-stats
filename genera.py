import pandas as pd
from pymongo import MongoClient
from gestionaDatos import Site

client = MongoClient()
#point the client at mongo URI
client = MongoClient()
#select database
db = client['test']
#select the collection within the database
sites = db.site
#convert entire collection to Pandas dataframe
sitios=Site.objects[:100000](finished=True, tech__exists=True)
tecnologias=dict()

for sitio in sitios:
    for tecnologia in sitio.tech:
        try:
            tecnologias[tecnologia] += 1
        except:
            tecnologias[tecnologia] = 1
listado = {'nombre': list(), 'cantidad': list()}
for tecnologia, value in tecnologias.items():
    listado['nombre'].append(tecnologia)
    listado['cantidad'].append(value)
df = pd.DataFrame.from_dict(listado)
df = df.sort_values(by='cantidad', ascending=False)
print(df.shape)


import matplotlib.pyplot as plt
tamano = 15
my_circle=plt.Circle( (0,0), 0.7, color='white')
plt.pie(df.head(tamano)['cantidad'], labels=df.head(tamano)['nombre'])
p=plt.gcf()
p.gca().add_artist(my_circle)
plt.show()
print (df.head(tamano))

import squarify
SMALL_SIZE = 5
MEDIUM_SIZE = 12
BIGGER_SIZE = 23
plt.figure(figsize=(10,10))
plt.rc('font', size=MEDIUM_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=BIGGER_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=BIGGER_SIZE)     # fontsize of the x and y labels
plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)   # fontsize of the figure title

squarify.plot(sizes=df.head(tamano)['cantidad'],
              label=df.head(tamano)['nombre'], alpha=.7)
plt.axis('off')
plt.show()


