from django import template

register = template.Library()


@register.filter
def addclass(field, css):
    return field.as_widget(attrs={"class": css})


def uglify(field):
    r = ""
    for i in range(len(field)):
        if i % 2 == 0:
            r += field[i].lower()
        else:
            r += field[i].upper()
    return r
