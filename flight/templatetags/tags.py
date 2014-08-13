from django import template
import markdown2
 
register = template.Library()
 
@register.filter
def md(text):
    return markdown2.markdown(text, extras=["markdown-in-html","nl2br","tables","wiki-tables"])

register.filter('md', md)