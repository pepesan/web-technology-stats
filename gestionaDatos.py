from datetime import datetime
from mongoengine import *

connected = False
try:
    connect(host='127.0.0.1', port=27017, db='test')
    connected = True
except Exception as e:
    print("No se puede conectar a la BBDD por lo que se finaliza la ejecución")
    print("No olvides arrancar la BBDD MongoDB, antes de ejecutar los scripts")
    print("Motivo: " + str(e))

if (connected == True):
    print("Se ha conectado al servidor")
else:
    exit(0)

BATCH = 2


class Site(DynamicDocument):
    url = StringField(required=True, unique=True)
    position = DecimalField(required=True)
    batch = DecimalField(required=True)
    retries = DecimalField(required=True, default=0)
    tech = ListField(StringField(max_length=60))
    last_search_datetime = DateTimeField(default=datetime.utcnow)
    finished = BooleanField(default=False)
    meta = {
        'indexes': [
            {
                'fields': ['url'],
                'unique': True
            },
            'finished',
            'position',
            'tech',
            'retries',
            'batch'
        ]
    }

    def __str__(self):
        return self.url + ":" + str(self.tech)

class SiteSpain(DynamicDocument):
    url = StringField(required=True, unique=True)
    position = DecimalField(required=False)
    batch = DecimalField(required=True)
    retries = DecimalField(required=True, default=0)
    tech = ListField(StringField(max_length=60))
    last_search_datetime = DateTimeField(default=datetime.utcnow)
    finished = BooleanField(default=False)
    meta = {
        'indexes': [
            {
                'fields': ['url'],
                'unique': True
            },
            'finished',
            'position',
            'tech',
            'retries',
            'batch'
        ]
    }

    def __str__(self):
        return self.url + ":" + str(self.tech)

class Resultado(DynamicDocument):
    tech = StringField(required=True)
    criterio = StringField(required=True)
    total = DecimalField(required=True)
    resultPercentage = FloatField(required=True, default=0)
    position = DecimalField(required=True)
    batch = DecimalField(required=True)
    resultString = StringField(required=False, default="")
    last_search_datetime = DateTimeField(default=datetime.utcnow)
    finished = BooleanField(default=False)

    meta = {
        'indexes': [
            'tech',
            'total',
            'position',
            'batch',
            'finished',
            'criterio'
        ]
    }

    def __str__(self):
        return str(self.position) + ":" + str(self.tech) + ":" + str(self.resultPercentage)

class ResultadoSpain(DynamicDocument):
    tech = StringField(required=True)
    criterio = StringField(required=True)
    total = DecimalField(required=True)
    resultPercentage = FloatField(required=True, default=0)
    position = DecimalField(required=True)
    batch = DecimalField(required=True)
    resultString = StringField(required=False, default="")
    last_search_datetime = DateTimeField(default=datetime.utcnow)
    finished = BooleanField(default=False)

    meta = {
        'indexes': [
            'tech',
            'total',
            'position',
            'batch',
            'finished',
            'criterio'
        ]
    }

    def __str__(self):
        return str(self.position) + ":" + str(self.tech) + ":" + str(self.resultPercentage)



def buscaSitio(id):
    return Site.objects(finished=False, _id=id)
