from django.views.generic import TemplateView


# Create your views here.
#  Vista basada en clases  
class IndexView(TemplateView):
    template_name = 'home.html'