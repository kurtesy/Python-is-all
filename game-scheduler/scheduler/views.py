from django.shortcuts import render
from django.http import HttpResponse
from week_scheduler.utils import get_streams


def game_event(request):
    if request.method == 'GET':
        return HttpResponse(request.GET)
    else:
        return HttpResponse('Kuch to gadbad h!!')
