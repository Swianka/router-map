from django import template

register = template.Library()


@register.inclusion_tag('tree_node.html')
def tree_node(visualisation):
    return {'visualisation': visualisation}
