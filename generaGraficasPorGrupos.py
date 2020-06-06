import pandas as pd
from bokeh.transform import factor_cmap

from gestionaDatos import *
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


def generate_sites(num, criterio):
    sitios = Site.objects.order_by('position')[:num](batch=BATCH, position__lte=num, finished=True, tech__exists=True, __raw__=criterio['query'])
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
    #print(listado)
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


def generateFigurePlotly(num, df, tamano, criterio, formats):
    colores = ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43"
               ]
    #print("DF Filtrado "+ str(df.head()))
    layout = go.Layout(
        autosize=False,
        width=1000,
        height=1000
    )
    fig = go.Figure(data=[go.Bar(
        x=df.head(tamano)['nombre'], y=df.head(tamano)['porcentajes'],
        text=df.head(tamano)['porcentajes'],
        marker_color=colores,
        textposition='auto',
    )], layout=layout)
    import base64
    with open("./data/logo.png", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    # add the prefix that plotly will want when using the string as source
    encoded_image = "data:image/png;base64," + encoded_string
    fig.add_layout_image(
        go.layout.Image(
            #source="http://cursosdedesarrollo.com/wp-content/uploads/2019/12/logo-cuadrado.png",
            source=encoded_image,
            #xref="x",
            #yref="y",
            xref="paper",
            yref="paper",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            sizing="stretch",
            opacity=0.1,
            layer="above")
    )
    fig.update_layout(
        title={
            'text': "Porcentaje de Uso de Tecnologías para " + str(num) + " sitios web: "+criterio['name'],
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        template="plotly_white")
    # fig.show()
    for f in formats:
        fig.write_image(
            REPORTDIR + "/" + criterio['name']+"/barras_plotly_" + str(num) + "_" + str(tamano) + "_"+str(criterio['name'])+"."+f
        )


def generateFigureBokeh(num, df, tamano):
    from bokeh.io import show, output_file
    from bokeh.models import ColumnDataSource
    from bokeh.io import export_png
    from bokeh.plotting import figure
    output_file("report/barras_bokeh_" + str(num) + ".html")

    colores = ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43","#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
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


def generateAndSavePlot(num, tamanos, criterio, formats):
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
    #print(df.head())
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
    #print(df.head())
    index = 1
    if(criterio['name']=="Todos"):
        for row in df.iterrows():
            #print("Fila: "+ str(row))
            try:
                data = Resultado.objects().get(tech=row[1][0], total=num, batch=BATCH)
                # print(data)
                data.delete()
            except Exception as e:
                print("resultado no encontrado")
            resultado = Resultado()
            resultado.criterio = criterio['name']
            resultado.tech = row[1][0]
            resultado.total = num
            resultado.resultDecimal = row[1][1]
            resultado.resultString = row[1][2]
            resultado.resultPercentage= row[1][3]
            resultado.finished = True
            resultado.position = index
            resultado.batch = BATCH

            #print("Resultado" + str(resultado))
            index += 1
            try:
                resultado.save()
                # print("Sitio Guardado: " + str(resultado))
            except Exception as e:
                print(e)

    for tamano in tamanos:
        #print(df.head(tamano))
        generateFigurePlotly(num, df, tamano, criterio, formats)
        # generateFigureBokeh(num, df, tamano)


if (os.path.isdir(REPORTDIR) == False):
    os.mkdir(REPORTDIR)

nums = [10, 50, 100, 500, 1000, 10000,
        100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000,
        1100000, 1200000, 1300000, 1400000]


tamanos = [10, 20, 30, 40, 50]
formats=['png', 'svg']
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
                    {'tech': 'Joomla'},
                     {'tech': "Liferay"},
                     {'tech': "Blogger"},
                     {'tech': "1C-Bitrix"},
                     {'tech': 'Wix'},
                  ]
        },
        'tech': ["WordPress", "Drupal", "Joomla", "Liferay", "Blogger", "1C-Bitrix", "Wix"]
    },
    {
        'name': 'Tiendas-Online',
        'query': {
                 '$or': [
                    {'tech': 'Magento'},
                    {'tech': 'WooCommerce'},
                    {'tech': 'PrestaShop'},

                    {'tech': "Shopify"}
                  ]
        },
        'tech': ["Magento", "WooCommerce", "PrestaShop", "Shopify"]
    },
    {
        'name': 'Sistemas-Operativos',
        'query': {
                 '$or': [
                    {'tech': 'Ubuntu'},
                    {'tech': 'Debian'},
                    {'tech': 'CentOS'},
                    {'tech': 'Fedora'},
                     {'tech': "Gentoo"},
                    {'tech': "Red Hat"},
                    {'tech': "UNIX"},
                    {'tech': "Windows Server"}
                  ]
        },
        'tech': ["Ubuntu", "Debian", "CentOS", "Fedora", "Red Hat", "UNIX", "Windows Server", "Gentoo"]
    },
    {
        'name': 'Servidores-Web',
        'query': {
                 '$or': [
                     {'tech': 'Apache'},
                     {'tech': 'IIS'},
                     {'tech': "IIS\\\\;confidence:50"},
                     {'tech': 'Nginx'},
                     {'tech': 'Tengine'},
                     {'tech': "LiteSpeed"}
                  ]
        },
        'tech': ["Apache", "IIS", "IIS\\\\;confidence:50", "Nginx", "Tengine", "Apache Tomcat", "LiteSpeed"]
    },
    {
        'name': 'BackendServerAppContainer',
        'query': {
                 '$or': [
                     {'tech': 'Java'},
                     {'tech': "Apache Tomcat"},
                     {'tech': 'PHP'},
                     {'tech': 'Python'},
                     {'tech': 'Ruby on Rails'},
                     {'tech': "Microsoft ASP.NET"},
                     {'tech': "Java Servlet"},
                     {'tech': 'Ruby'},
                     {'tech': 'Node.js'},
                     {'tech': "Express"},
                     {'tech': 'Ruby on Rails'},
                     {'tech': "Lua"},
                     {'tech': "OpenResty"},
                     {'tech': "OpenGSE"},
                  ]
        },
        'tech': ["Apache Tomcat", "Java", "PHP", "Python", "Ruby on Rails", "Microsoft ASP.NET",
                 "Java Servlet", 'Ruby', "Node.js", "Ruby on Rails", "Lua", "OpenResty",
                 "Express", "OpenGSE"]
    },
    {
        'name': 'DataBases',
        'query': {
                 '$or': [
                     {'tech': "MySQL"},
                     {'tech': "PostgreSQL"},
                     {'tech': "MariaDB"},
                     {'tech': "MongoDB"},
                     {'tech': "Percona"},
                     {'tech': "SQLite"}
                  ]
        },
        'tech': ["MySQL", "PostgreSQL", "MariaDB", "MongoDB", "Percona", "SQLite"]
    },
    {
        'name': 'RRSS',
        'query': {
                 '$or': [
                     {'tech': "Facebook"},
                     {'tech': "Twitter"},
                     {'tech': "Pinterest"},
                     {'tech': "Linkedin"},
                     {'tech': "YouTube"},
                     {'tech': "Google Plus"}
                  ]
        },
        'tech': ["Facebook", "Twitter", "Pinterest", "Linkedin", "YouTube", "Google Plus"]
    },
    {
        'name': 'WP-Plugins',
        'query': {
                 '$or': [
                     {'tech': 'Yoast SEO'},
                     {'tech': 'WordPress Super Cache'},
                     {'tech': 'Elementor'},
                     {'tech': "All in One SEO Pack"},
                     {'tech': "AddThis"},
                     {'tech': "W3 Total Cache"},
                     {'tech': "WP Rocket"},
                     {'tech': "Gravity Forms"},
                     {'tech': 'AMP Plugin'}
                  ]
        },
        'tech': ['Yoast SEO', 'WordPress Super Cache', 'Elementor', "All in One SEO Pack", "AddThis",
                 "W3 Total Cache", "WP Rocket", "Gravity Forms", 'AMP Plugin']
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
                     {'tech': "Vue.js"},
                     {'tech': "MooTools"},
                     {'tech': "Backbone.js"}
                  ]
        },
        'tech': ["Angular", "Angular JS", "React", "jQuery", "jQuery UI", "jQuery Mobile", "Vue", "Vue.js",
                 "MooTools", "Backbone.js"]
    },
    {
        'name': 'VariousTech',
        'query': {
                 '$or': [
                     {'tech': "Font Awesome"},
                     {'tech': "Material Design Lite"},
                     {'tech': "Bootstrap"},
                     {'tech': "ZURB Foundation"},
                     {'tech': "jQuery UI"},
                     {'tech': "jQuery Mobile"},
                     {'tech': "Ionic"},
                     {'tech': "UIKit"},
                     {'tech': "Materialize CSS"},
                     {'tech': "animate.css"},
                     {'tech': "Lightbox"},
                     {'tech': 'DataTables'},
                     {'tech': "OWL Carousel"},
                     {'tech': 'Modernizr'},
                     {'tech': 'CloudFlare'},
                     {'tech': 'reCAPTCHA'},
                     {'tech': "Sucuri"},
                     {'tech': "Akamai"},
                     {'tech': 'Varnish'},
                     {'tech': "Slick"},
                     {'tech': "Revslider"},
                     {'tech': "OpenSSL"},
                     {'tech': "Underscore.js"},
                     {'tech': "FancyBox"},
                     {'tech': "Liveinternet"},
                     {'tech': "Plesk"},
                     {'tech': "Swiper Slider"},
                     {'tech': "MailChimp"},
                     {'tech': "prettyPhoto"},
                     {'tech': "RequireJS"},
                     {'tech': "Gravatar"},
                     {'tech': "Moment.js"},
                     {'tech': "Litespeed Cache"},
                     {'tech': "Polyfill"},
                     {'tech': "Handlebars"},
                     {'tech': "TrackJs"},
                     {'tech': "SWFObject"},
                     {'tech': "Select2"},
                     {'tech': "SiteGround"},
                     {'tech': "SquareSpace"},
                     {'tech': "FlexSlider"},
                     {'tech': "comScore"},
                     {'tech': "Clipboard.js"},
                     {'tech': "TweenMax"},
                     {'tech': "Prototype"},
                     {'tech': "Lazy.js"},
                     {'tech': "Ionicons"},
                     {'tech': "Chart.js"}
                  ]
        },
        'tech': ["Font Awesome", "Material Design Lite", "Bootstrap", "ZURB Foundation", "jQuery UI",
                 "jQuery Mobile", "Ionic", "UIKit", "Materialize CSS", "animate.css", "Lightbox",
                 'DataTables', "OWL Carousel", "TrackJs", "SWFObject", "Select2", "SiteGround"
                 'Modernizr', 'CloudFlare', 'reCAPTCHA', "Sucuri", "SquareSpace", "FlexSlider"
                 "Akamai", 'Varnish', "Slick", "Revslider", "OpenSSL", "Underscore.js", "FancyBox",
                 "Liveinternet",  "Swiper Slider",  "Plesk",  "MailChimp", "prettyPhoto",
                 "RequireJS", "Gravatar", "Moment.js", "Litespeed Cache", "Polyfill", "Handlebars",
                 "comScore", "Clipboard.js", "TweenMax", "Prototype", "Lazy.js", "Ionicons", "Chart.js"]
    },
    {
        'name': 'Amazon-Tech',
        'query': {
                 '$or': [
                     {'tech': "Amazon Web Services"},
                     {'tech': "Amazon CloudFront"},
                     {'tech': 'Amazon S3'},
                     {'tech': 'Amazon EC2'}
                  ]
        },
        'tech': ["Amazon Web Services", "Amazon CloudFront", 'Amazon S3', 'Amazon EC2']
    },
    {
        'name': 'Google',
        'query': {
                 '$or': [
                     {'tech': "Google Tag Manager"},
                     {'tech': "Google AdSense"},
                     {'tech': "YouTube"},
                     {'tech': "reCAPTCHA"},
                     {'tech': "Google Plus"},
                     {'tech': "Google Font API"},
                     {'tech': 'Google Analytics'},
                     {'tech': "Google Maps"},
                     {'tech': "Google PageSpeed"},
                     {'tech': "DoubleClick for Publishers (DFP)"}
                  ]
        },
        'tech': ["Google Tag Manager", "Google AdSense", "YouTube", "reCAPTCHA", "Google Plus",
                 "Google Font API", "Google Analytics", "Google Maps", "Google PageSpeed",
                 "DoubleClick for Publishers (DFP)"]
    }

]
cms=[

    {
        'name': 'CMSs',
        'query': {
                 '$or': [
                    {'tech': 'WordPress'},
                    {'tech': 'Drupal'},
                    {'tech': 'Joomla'},
                     {'tech': "Liferay"},
                     {'tech': "Blogger"},
                     {'tech': "OpenGSE"},
                     {'tech': "1C-Bitrix"}
                  ]
        },
        'tech': ["WordPress", "Drupal", "Joomla", "Liferay", "Blogger", "OpenGSE", "1C-Bitrix"]
    }
]

#criterios = [{'name': 'Todos','query': {},'tech': None},]
#nums = [100]
BATCH = 1
for criterio in criterios:
    if (os.path.isdir(REPORTDIR + "/" +criterio['name']) == False):
        os.mkdir(REPORTDIR+ "/" +criterio['name'])
    #print(criterio)
    print("Criterio: " + str(criterio['name']))
    for num in nums:
        generateAndSavePlot(num, tamanos, criterio, formats)


#generateAndSavePlot(10000, tamanos, criterios[1])
"""
generate_Circle(20, df)

generate_squarify(20, df)
"""
