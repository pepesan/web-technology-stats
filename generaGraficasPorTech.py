import pandas as pd
from bokeh.transform import factor_cmap

from gestionaDatos import *
import os
import matplotlib.pyplot as plt
import squarify
import plotly.graph_objects as go

REPORTDIR = 'report'
BATCH = 1

if (os.path.isdir(REPORTDIR) == False):
    os.mkdir(REPORTDIR)

nums = [10, 50, 100, 500, 1000, 10000,
        100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000
        ]
#nums = [100]
formats=['png', 'svg']
criterios = [

    {
        'name': 'CMSs',
        'query': {
                 '$or': [
                    {'tech': 'WordPress'},
                    {'tech': 'Drupal'},
                    {'tech': 'Joomla'},
                     {'tech': "Liferay"},
                     {'tech': "Blogger"},
                     {'tech': "1C-Bitrix"}
                  ]
        },
        'tech': ["WordPress", "Drupal", "Joomla", "Liferay", "Blogger", "1C-Bitrix"]
    },
    {
        'name': 'Tiendas-Online',
        'query': {
                 '$or': [
                    {'tech': 'Magento'},
                    {'tech': 'WooCommerce'},
                    {'tech': 'PrestaShop'},
                    {'tech': 'Wix'},
                    {'tech': "Shopify"}
                  ]
        },
        'tech': ["Magento", "WooCommerce", "PrestaShop", "Wix", "Shopify"]
    },
    {
        'name': 'Sistemas-Operativos',
        'query': {
                 '$or': [
                    {'tech': 'Ubuntu'},
                    {'tech': 'Debian'},
                    {'tech': 'CentOS'},
                    {'tech': 'Fedora'},
                    {'tech': "Red Hat"},
                    {'tech': "UNIX"},
                    {'tech': "Windows Server"}
                  ]
        },
        'tech': ["Ubuntu", "Debian", "CentOS", "Fedora", "Red Hat", "UNIX", "Windows Server"]
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
                     {'tech': "Percona"}
                  ]
        },
        'tech': ["MySQL", "PostgreSQL", "MariaDB", "MongoDB", "Percona"]
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
                     {'tech': "Twitter"},
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
                 "Liveinternet",  "Swiper Slider",  "Plesk",  "MailChimp", "Twitter", "prettyPhoto",
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


def generatePlot(tech, techResults):
    colores = ["#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b", "#fdae61", "#f46d43",
               "#d53e4f", "#9e0142", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43", "#5e4fa2", "#3288bd", "#66c2a5", "#abdda4", "#e6f598", "#ffffbf", "#fee08b",
               "#fdae61", "#f46d43",
               ]
    layout = go.Layout(
        autosize=False,
        width=1000,
        height=1000
    )
    totales = []
    porcentajes = []
    cadenas = []
    for result in techResults:
        totales.append(str(int(result.total))+"s")
        porcentajes.append(result.resultPercentage)
        cadenas.append(result.resultString)

    print(totales)
    print(porcentajes)
    print(cadenas)
    fig = go.Figure(data=[go.Bar(x=totales, y=porcentajes, text=cadenas, marker_color=colores, textposition='auto', )],
                    layout=layout)
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
            'text': "Porcentaje de Uso de " + tech + " para distintos número de sitios web",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        template="plotly_white")
    # fig.show()
    for f in formats:
        fig.write_image(
            "report/" + str(tech) + "_barras_plotly." + f
        )

def generatePlotByTech(tech, formats):
    techResults= Resultado.objects.filter(tech=tech).order_by('total')
    print(tech)


    generatePlot(tech, techResults)

for criterio in criterios:
    print("Criterio: " + str(criterio['name']))
    for tech in criterio['tech']:
        generatePlotByTech(tech, formats)






