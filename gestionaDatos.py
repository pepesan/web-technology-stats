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

    def __str__(self):
        return self.url + ":" + str(self.tech)






def buscaSitio(id):
    return Site.objects(finished=False, _id=id)
