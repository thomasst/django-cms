from django.conf import settings

def to_utf8(string):
    if isinstance(string, str):
        return unicode(string, 'utf8')
    else:
        return string
    
def from_utf8(string):
    if isinstance(string, unicode):
        return string.encode('utf8')
    else:
        return string

def flatten(lst):
    for elem in lst:
        if isinstance(elem, list) or isinstance(elem, tuple):
            for i in flatten(elem):
                yield i
        else:
            yield elem

def get_values(object, fields):
    return dict([(field, getattr(object, field)) for field in fields])
def get_dict(fields, values):
    return dict([(field, from_utf8(values[field])) for field in fields])
def set_values(object, fields, values):
    for field in fields:
        setattr(object, field, from_utf8(values[field]))

def language_list():
    return [l[0] for l in settings.LANGUAGES]