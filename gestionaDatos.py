from datetime import datetime
from mongoengine import *

connect(host='127.0.0.1', port=27017, db='test')


class Site(DynamicDocument):
    url = StringField(required=True, unique=True)
    position = DecimalField(required=True)
    retries = DecimalField(required=True, default=0)
    tech = ListField(StringField(max_length=60))
    last_search_datetime = DateTimeField(default=datetime.utcnow)
    finished = BooleanField(default=False)
    meta = {
        'indexes': [
            'url',
            'finished',
            'tech',
            'retries'
        ]
    }

    def __str__(self):
        return self.url + ":" + str(self.tech)

class Resultado:
    tech = StringField(required=True, unique=True)
    total = DecimalField(required=True)
    resultDecimal = DecimalField(required=True, default=0)
    resultPercentage = FloatField(required=True, default=0)
    last_search_datetime = DateTimeField(default=datetime.utcnow)
    finished = BooleanField(default=False)
    meta = {
        'indexes': [
            'tech',
            'total',
            'finished'
        ]
    }




def buscaSitio(id):
    return Site.objects(finished=False, _id=id)
