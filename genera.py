import pandas as pd
from bokeh.transform import factor_cmap

from gestionaDatos import *
import os
import matplotlib.pyplot as plt
import squarify
import plotly.graph_objects as go

REPORTDIR = 'report'
BATCH = 1

"""
Para cuando falle el bloque de ordenado
Ejecutar directamente en mongo
db.adminCommand({"setParameter": 1, "internalQueryExecMaxBlockingSortBytes" :134217728}) 

Referencia:
http://pe-kay.blogspot.com/2016/05/how-to-change-mongodbs-sort-buffer-size.html
"""


def generate_sites(num, criterio):
    sitios = Site.objects.order_by('position')[:num](finished=True, tech__exists=True, __raw__=criterio['query'])
    tecnologias = dict()

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

    dataframe = pd.DataFrame.from_dict(listado)
    dataframe = dataframe.sort_values(by='cantidad', ascending=False)
    listado = {'nombre': list(), 'cantidad': list()}
    for row in dataframe.iterrows():
        # print("row[1][1]: "+ str(row[1][0]))
        # print("row[1][2]: " + str(row[1][1]))
        listado['nombre'].append(row[1][0])
        listado['cantidad'].append(row[1][1])
    dataframe = pd.DataFrame.from_dict(listado)
    # print(dataframe.shape)
    del sitios
    return dataframe


def generate_Circle(tamano, df):
    my_circle = plt.Circle((0, 0), 0.7, color='white')
    plt.pie(df.head(tamano)['cantidad'], labels=df.head(tamano)['nombre'])
    p = plt.gcf()
    p.gca().add_artist(my_circle)
    plt.show()
    plt.savefig(REPORTDIR + '/circle_' + str(tamano) + '.png', bbox_inches='tight')


def generate_squarify(tamano, df):
    SMALL_SIZE = 5
    MEDIUM_SIZE = 12
    BIGGER_SIZE = 23
    plt.figure(figsize=(10, 10))
    plt.rc('font', size=MEDIUM_SIZE)  # controls default text sizes
    plt.rc('axes', titlesize=BIGGER_SIZE)  # fontsize of the axes title
    plt.rc('axes', labelsize=BIGGER_SIZE)  # fontsize of the x and y labels
    plt.rc('xtick', labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=MEDIUM_SIZE)  # fontsize of the tick labels
    plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

    squarify.plot(sizes=df.head(tamano)['cantidad'],
                  label=df.head(tamano)['nombre'], alpha=.7)
    plt.axis('off')
    plt.show()
    plt.savefig(REPORTDIR + '/squarify_' + str(tamano) + '.png', bbox_inches='tight')
    plt.close()


def printAllDF(df):
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
        print(df)


def generateFigurePlotly(num, df, tamano, criterio):
    colores = ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43"]
    #print("DF Filtrado "+ str(df.head()))
    fig = go.Figure(data=[go.Bar(
        x=df.head(tamano)['nombre'], y=df.head(tamano)['porcentajes'],
        text=df.head(tamano)['porcentajes'],
        marker_color=colores,
        textposition='auto',
    )])
    fig.update_layout(
        title={
            'text': "Porcentaje de Uso de Tecnologías para " + str(num) + " sitios web: "+criterio['name'],
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'})
    # fig.show()
    fig.write_image("report/barras_plotly_" + str(num) + "_" + str(tamano) + "_"+str(criterio['name'])+".png")


def generateFigureBokeh(num, df, tamano):
    from bokeh.io import show, output_file
    from bokeh.models import ColumnDataSource
    from bokeh.io import export_png
    from bokeh.plotting import figure
    output_file("report/barras_bokeh_" + str(num) + ".html")

    colores = ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43"]
    source = ColumnDataSource(df.head(tamano))
    cyl_cmap = factor_cmap('nombre', palette=colores, factors=sorted(df.head().nombre.unique()))
    p = figure(plot_height=350, x_range=df.head(tamano)['nombre'], title="MPG by # Cylinders",
               toolbar_location=None, tools="")

    p.vbar(x='nombre', top='cantidad', width=1, source=source, line_color=cyl_cmap, fill_color=cyl_cmap)

    p.title.text = 'Tecnologías'
    show(p)
    # export_png(p, filename="report/plot.png")


def generateAndSavePlot(num, tamanos, criterio):
    print("Número de Resultados: " + str(num))
    df = generate_sites(num, criterio)
    if (criterio['tech']!= None):
        listado = {'nombre': list(), 'cantidad': list()}
        for row in df.iterrows():
            # print("row[1][1]: "+ str(row[1][0]))
            # print("row[1][2]: " + str(row[1][1]))
            # print(str(row[1]['nombre']))
            for tech in criterio['tech']:
                #print(tech)
                if (tech == row[1]['nombre']):
                    listado['nombre'].append(row[1][0])
                    listado['cantidad'].append(row[1][1])
        df = pd.DataFrame.from_dict(listado)
    porcentajes = list()
    porcentajesFloat = list()
    textos = list()
    index = 0
    for valor in df['cantidad']:
        porcentaje = valor / num
        cadenaPorcentaje = "{:.2%}".format(porcentaje)
        porcentajes.append(cadenaPorcentaje)
        porcentajesFloat.append(porcentaje)
        textos.append(df['nombre'][index] + ": " + cadenaPorcentaje)
        index += 1
    df['porcentajes'] = porcentajes
    df['porcentajesFloat'] = porcentajesFloat
    df['textos'] = textos
    index = 1
    for row in df.iterrows():
        try:
            data = Resultado.objects().get(tech=row[1][0], total=num, batch=BATCH)
            # print(data)
            data.delete()
        except Exception as e:
            print("resultado no encontrado")

        resultado = Resultado()
        resultado.tech = row[1][0]
        resultado.total = num
        resultado.resultDecimal = row[1][3]
        resultado.resultString = row[1][2]
        resultado.finished = True
        resultado.position = index
        resultado.batch = BATCH
        index += 1
        try:
            resultado.save()
            # print("Sitio Guardado: " + str(resultado))
        except Exception as e:
            print(e)

    for tamano in tamanos:
        print(df.head(tamano))
        generateFigurePlotly(num, df, tamano, criterio)
        # generateFigureBokeh(num, df, tamano)


if (os.path.isdir(REPORTDIR) == False):
    os.mkdir(REPORTDIR)

nums = [10, 50, 100, 500, 1000, 10000, 100000, 200000, 300000, 400000, 500000, 600000]
#nums = [100]
tamanos = [10, 20]
criterios = [
    {
        'name': 'Todos',
        'query': {},
        'tech': None
    },
    {
        'name': 'CMSs',
        'query': {
                 '$or': [
                    {'tech': 'WordPress'},
                    {'tech': 'Drupal'},
                    {'tech': 'Joomla'}
                  ]
        },
        'tech': ["WordPress", "Drupal", "Joomla"]
    },
    {
        'name': 'Servers',
        'query': {
                 '$or': [
                     {'tech': 'Apache'},
                     {'tech': 'IIS'},
                     {'tech': 'Nginx'},
                     {'tech': 'Tengine'},
                     {'tech': "Apache Tomcat"}
                  ]
        },
        'tech': ["Apache", "IIS", "Nginx", "Tengine", "Apache Tomcat"]
    },
    {
        'name': 'Servers',
        'query': {
                 '$or': [
                     {'tech': 'Java'},
                     {'tech': 'PHP'},
                     {'tech': 'Python'},
                     {'tech': 'Ruby on Rails'},
                     {'tech': "Microsoft ASP.NET"},
                     {'tech': "Java Servlet"}
                  ]
        },
        'tech': ["Java", "PHP", "Python", "Ruby on Rails", "Microsoft ASP.NET", "Java Servlet"]
    },
    {
        'name': 'DataBases',
        'query': {
                 '$or': [
                     {'tech': "MySQL"},
                     {'tech': "PostgreSQL"},
                     {'tech': "MariaDB"},
                     {'tech': "MongoDB"}
                  ]
        },
        'tech': ["MySQL", "PostgreSQL", "MariaDB", "MongoDB"]
    },
    {
        'name': 'JSFrameWorks',
        'query': {
                 '$or': [
                     {'tech': "Angular"},
                     {'tech': "Angular JS"},
                     {'tech': "React"},
                     {'tech': "jQuery"},
                     {'tech': "jQuery UI"},
                     {'tech': "jQuery Mobile"},
                     {'tech': "Vue"},
                     {'tech': "Vue.js"}
                  ]
        },
        'tech': ["Angular", "Angular JS", "React","jQuery", "jQuery UI", "jQuery Mobile", "Vue", "Vue.js"]
    }
]


for criterio in criterios:
    for num in nums:
        generateAndSavePlot(num, tamanos, criterio)


#generateAndSavePlot(10000, tamanos, criterios[1])
"""
generate_Circle(20, df)

generate_squarify(20, df)
"""
