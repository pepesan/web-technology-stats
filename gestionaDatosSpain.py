from datetime import datetime
from mongoengine import *

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
