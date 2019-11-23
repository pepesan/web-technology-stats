import pandas as pd
from bokeh.transform import factor_cmap

from gestionaDatos import Site
import os
import matplotlib.pyplot as plt
import squarify
import plotly.graph_objects as go
REPORTDIR = 'report'

"""
Para cuando falle el bloque de ordenado
Ejecutar directamente en mongo
db.adminCommand({"setParameter": 1, "internalQueryExecMaxBlockingSortBytes" :134217728}) 

Referencia:
http://pe-kay.blogspot.com/2016/05/how-to-change-mongodbs-sort-buffer-size.html
"""


def generate_sites(num):
    sitios = Site.objects.order_by('position')[:num](finished=True, tech__exists=True)
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
    print(dataframe.shape)
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

def generateFigurePlotly(num,df,tamano):
    fig = go.Figure(data=[go.Bar(
                x=df.head(tamano)['nombre'], y=df.head(tamano)['porcentajes'],
                text=df.head(tamano)['porcentajes'],
                textposition='auto',
            )])
    fig.update_layout(
        title={
            'text': "Porcentaje de Uso de Tecnologías para "+str(num)+ " sitios web",
            'y':0.9,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'})
    fig.show()
    fig.write_image("report/barras_plotly_"+str(num)+"_"+str(tamano)+".png")
def generateFigureBokeh(num,df,tamano):
    from bokeh.io import show, output_file
    from bokeh.models import ColumnDataSource
    from bokeh.io import export_png
    from bokeh.plotting import figure
    output_file("report/barras_bokeh_"+str(num)+".html")

    colores=["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43", "#d53e4f", "#9e0142","#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43"]
    source = ColumnDataSource(df.head(tamano))
    cyl_cmap = factor_cmap('nombre', palette=colores, factors=sorted(df.head().nombre.unique()))
    p = figure(plot_height=350, x_range=df.head(tamano)['nombre'], title="MPG by # Cylinders",
               toolbar_location=None, tools="")

    p.vbar(x='nombre', top='cantidad', width=1, source=source, line_color=cyl_cmap, fill_color=cyl_cmap)

    p.title.text = 'Tecnologías'
    show(p)
    #export_png(p, filename="report/plot.png")
def generateAndSavePlot(num,tamano):
    print("Número de Resultados: " + str(num))
    df = generate_sites(num)
    porcentajes = list()
    textos = list()
    index=0
    for valor in df['cantidad']:
        porcentaje=valor/num
        cadenaPorcentaje="{:.2%}".format(porcentaje)
        porcentajes.append(cadenaPorcentaje)
        textos.append(df['nombre'][index] + ": "+cadenaPorcentaje)
        index += 1
    df['porcentajes'] = porcentajes
    df['textos'] = textos
    print(df.head(tamano))
    generateFigurePlotly(num, df, tamano)
    #generateFigureBokeh(num, df, tamano)



if(os.path.isdir(REPORTDIR) == False):
    os.mkdir(REPORTDIR)

nums = [10, 100, 500, 1000, 10000, 100000, 200000, 300000, 400000]
#nums= [100]
tamanos = [10, 20]
for tamano in tamanos:
    for num in nums:
        generateAndSavePlot(num, tamano)



"""
generate_Circle(20, df)

generate_squarify(20, df)
"""
