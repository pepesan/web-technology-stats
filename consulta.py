from gestionaDatos import *
BATCH = 1
criterios = [{
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
    }]
sitios = Site.objects.order_by('last_search_datetime')[:100](batch=BATCH, finished=True, tech__exists=True, __raw__=criterios[0]['query'])
print("sitios" + str(sitios))