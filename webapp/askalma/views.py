from django.views import generic
from .models import *
from django.views.generic import CreateView , UpdateView , DeleteView
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render


class QDetailView (generic.DetailView):
    model = Question
    template_name = "askalma/qdetail.html"

def index(request):
	return render(request, 'index.html')
def listing(request):
	return render(request, 'listing.html')
def postquestion(request):
	return render(request, 'post-question.html')
