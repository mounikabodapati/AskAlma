from django.http import HttpResponseRedirect, JsonResponse
from django.views import generic
from django.template import RequestContext
from django.urls import reverse
from django.shortcuts import redirect
from .models import *
from django.shortcuts import render
import time
from django.views.decorators.csrf import csrf_exempt
from elasticsearch import Elasticsearch
from urlparse import urlparse
import gdata.client
import gdata.gauth
import json
# from wordVectorClassifier import machineLearning
import gdata.photos.service #In this example where contacting Google Picasa Web API
# from gensim.models import word2vec


es = Elasticsearch("search-askalma-ec4hakudbwu54iw5gnp6k6ggpy.us-east-1.es.amazonaws.com", port=443,
				   use_ssl='true')


def _isLoggedIn(request):
	try:
		email = request.session['email']
		last_in = request.session['last_in']
		#Thirty minute old sessions are killed
		if (time.time()- last_in > 1800):
			return HttpResponseRedirect(reverse('social:begin' ,args=('google-oauth2',)))
		request.session['last_in'] = time.time()
		return None
	except KeyError:
		return HttpResponseRedirect(reverse('social:begin' ,args=('google-oauth2',)))

@csrf_exempt
def index(request):
	#Add these two lines to any page that requires user to be logged in
	result = _isLoggedIn(request)
	if result != None: return result
	result= getquestions(request)
	context = {}
	context['stats'] = _getStats()
	#if result.get('question')!="nothing":
	#	return result
	return render(request, 'askalma/index.html', context=context)

def search(request):
	context = {}
	response = getquestions(request)
	if response.get('questions') == "": return render(request, 'askalma/index.html', context=context)
	return response
	#return render(request, 'askalma/listing.html' , context = context)

def getquestions(request):
	searchstring= str(request.GET.get('querystring', ' '))
	print searchstring
	try:
		result=es.search(index='questions1', body={"from" : 0, "size" : 1000, "query":{ "query_string": { "query": searchstring, "default_field": 'title' }}})
		result=result['hits']['hits']
		print result
		b=[]
		for q in result:
			tags= q['_source']['tags']
			taglist= [s.strip() for s in tags.split(',')]
			a = {
			"title": q['_source']['title'],
			"taglist": taglist,
			"details": q['_source']["details"]
			}
			b.append(a)
			print(b)
		return JsonResponse({'questions': b })
	except KeyError:
		return JsonResponse({'questions': "nothing"})

def listing(request):
	result = _isLoggedIn(request)
	if result != None: return result
	response= searchquestion(request)
	return render(request, 'askalma/listing.html'  , context = response)


def searchquestion(request):
	try:
		#print "taking questions from elasticsearch"
		result=es.search(index='questions1', body={"from" : 0, "size" : 1000, "query":{"match_all": {}}})
		#print result
		questions= result['hits']['hits']
		#print questions
		b= []
		for question in questions:
			#print question
			tags= question['_source']['tags']
			taglist= [s.strip() for s in tags.split(',')]
			a = {
			"title": question['_source']['title'],
			"taglist": taglist,
			"details": question['_source']["details"],
			"qid" : question['_id']
			}
			b.append(a)
		#print b
		return {'questions': b }
	except KeyError:
		return {'questions': "nothing"}

@csrf_exempt
def postquestion(request):
	result = pullquestion(request)
	if result== "data":
		return render(request, 'askalma/listing.html')
	else:
		return render(request, 'askalma/post-question.html')

def pullquestion(request):
	try:
		#print "sending question to elasticsearch"
		title= str(request.GET.get("title", ' '))
		#print title
		tags= str(request.GET.get("tags", ' '))
		#print tags
		details= str(request.GET.get("details", ' '))

		#print details
		#print "inside es working"
		user_profile =_get_user_profile (request.session['email'])
		user_email= user_profile['email']
		user= es.search(index='users', body={"from" : 0, "size": 1000, "query":{ "query_string": {"query": user_email, "default_field": "email"}}})["hits"]["hits"]
		for u in user:
			user_id= u.get("_id")
			es.update(index= 'users', doc_type="user", id= user_id, body= {"doc": {"user_questions": " "+title}})
		doc = {
			"title": title,
			"tags": tags,
			"details": details,
			"user_id":user_id
		}
		if title!=" ":
			es.index(index="questions1", doc_type='question', body=doc)
			print doc
		return HttpResponseRedirect("data")
	except KeyError:
		return HttpResponseRedirect("webpage")

def profile (request):
	result = _isLoggedIn(request)
	if result != None: return result

	user_info = _get_user_profile (request.session['email'])
	context = {'user_info' : user_info}
	#print context
	return render(request, 'askalma/profile.html' , context)

def edit_profile (request ):
	result = _isLoggedIn(request)
	if result != None: return result

	user_info =_get_user_profile (request.session['email'])
	context = {'user_info' : user_info}
	return render(request , 'askalma/profile-setting.html', context= context)

def logout(request):
	try:
		del request.session['email']
	except:
		pass
	return index(request)

def contactus (request):
	pass

@csrf_exempt
def qdetail(request, qid):
	# ADD LOGIN
	context = _get_question_details (qid)
	return render(request, 'askalma/question_detail.html' , context = context)


def _get_question_details( qid):
	query = es.get(index="questions1", doc_type='question' , id=qid)
	question = query ['_source']
	question['id']  = query['_id']
	#answers = es.search ("doc is query for questions = qid ")
	answers = None
	return {'question' : question , 'answers' : answers}

#JUST UNCOMMENT the two lines
def _getStats ():
	stats = {}
	stats['views'] = 7812
	stats['questions'] = es.search(index='questions1', body={"size": 0,})['hits']['total']
	# stats['answersed_questions'] = es.search(index='questions', body={"size": 0,"query":{ "query_string": { "query": 1, "default_field": 'answered' }}})['hits']['total']
	stats['users'] =  es.search(index='users', body={"size": 0,})['hits']['total']
	stats['answered_questions'] = 147

	return stats

def iindex(request):
	#While this should an error page, it seems that it is nothing too serious, just redirect to index
	return index(request)


def process_auth(details,strategy,request,**kwargs):
	#Add user info to session, to keep them logged in
	strategy.session_set('email', details['email'])
	strategy.session_set('last_in', time.time())
	strategy.session_set('first_name', details['first_name'])
	strategy.session_set('last_name', details['last_name'])
	strategy.session_set('last_name', details['last_name'])
	#Check if they exist in ES. IF not, add them.
	count = es.search(index='users', body={"size": 0,"query":{ "query_string": { "query": details['email'] , "default_field": 'email' }}})['hits']['total']
	if count == 0:
		doc = {
			"email": details['email'],
			"last_name": details['last_name'],
			"headline" : "Student at Columbia University",
			"profile_pic" : "default.jpg"
		}
		es.index(index="users", doc_type='user', body=doc)

def _get_user_profile (email):
	res = es.search(index='users', body={"from": 0, "size": 1, "query": {
		"query_string": {"query": email, "default_field": 'email'}}})
	return res['hits']['hits'][0]['_source'], res['hits']['hits'][0]['_id']

def interest(request):
	context = {}
	response = getinterests(request)
	if response.get('questions') == "": return render(request, 'askalma/index.html', context=context)
	return response
	#return render(request, 'askalma/listing.html' , context = context)

def getinterests(request):
	searchstring= str(request.GET.get('querystring', ' '))
	try:
		response = machineLearning(searchstring)
		recommendations = []
		for i in range(len(response)):
			a = {
				"interest": response[i][0]
			}
			recommendations.append(a)
		print(recommendations)

		# Delete bottom stuff
		return JsonResponse({'interests': recommendations })
	except KeyError:
		return JsonResponse({'interests': "nothing"})

@csrf_exempt
def submit_answer(request):
	answer_text= str(request.POST.get("answer", None)) #getting answer_text
	question_id= str(request.POST.get("qid", None)) #getting answer_text
	profile, user_id = _get_user_profile (request.session['email'])

	if answer_text!= None:
		doc = {
			"answer_text":answer_text,
			"user_id": user_id,
			"question_id": question_id
		}
		es.index(index='answers3', doc_type='answer', body=doc)
		return HttpResponseRedirect('question-detail/%s'%question_id)
