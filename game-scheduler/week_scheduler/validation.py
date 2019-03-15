# -*- coding: utf-8 -*-
"""
Created on Wed Feb 20 12:45:18 2019
@author: npatel
Decription: Validation cases for game creation and updation.
"""
import datetime
import json
from week_scheduler import utils
from .models import EventLogsModel

BUFFER = 5    # Define number of seconds for game finish time buffer


def validate_csv(file_data):
    ctr = 0
    error_rows = []
    for row in file_data:
        ctr += 1
        if not row['stream_id']:
            continue
        else:
            print(check_id(row['stream_id']) , check_id(row['game_id'])
               , check_datetime(row['start_time']) , check_datetime(row['end_time'])
               , (not row['limit'].strip() or check_id(row['linked_room'])) , check_list(row['dow'])
               , (not row['limit'].strip() or check_datetime(row['limit'])))
            if not (check_id(row['stream_id']) and check_id(row['game_id'])
               and check_datetime(row['start_time']) and check_datetime(row['end_time'])
               and (not row['limit'].strip() or check_id(row['linked_room'])) and check_list(row['dow'])
               and (not row['limit'].strip() or check_datetime(row['limit']))):
                error_rows.append(ctr)
    return error_rows


def check_id(field):
    try:
        int(str(field))
        return True
    except ValueError:
        return False


def check_datetime(field):
    field = field.replace('"', '')
    try:
        datetime.datetime.strptime(field, '%Y-%m-%d %H:%M')
        return True
    except (TypeError, ValueError):
        return False


def check_list(field):
    if isinstance(field, str):
        return isinstance(json.loads(field), list)
    if isinstance(field, type(None)):
        return False
    return isinstance(field, list)


def linked_game(original, current):
    pass


def consecutive_events(stream_id, start, end):
    prev_event, next_event = fetch_prev_next_event(stream_id, start, end)
    prev_end = '1970-01-01'
    next_end = '3000-01-01'
    prev_duration = next_duration = 0
    if not prev_event:
        return False
    """Previous event"""
    if prev_event:
        prev_end = prev_event['end']
        prev_game_info = utils.extract_info(prev_event['title'])
        prev_game_id = prev_game_info['game_id']
        prev_duration = estimated_game_finish(prev_game_id)
    """Next event"""
    if next_event:
        next_start = next_event['start']
        next_game_info = utils.extract_info(next_event['title'])
        next_game_id = next_game_info['game_id']
        next_duration = estimated_game_finish(next_game_id)
    if (prev_event and utils.todatetime(start) - utils.todatetime(prev_end) <= datetime.timedelta(seconds=prev_duration) ) or\
       (next_event and utils.todatetime(next_start) - utils.todatetime(end) <= datetime.timedelta(seconds=next_duration)):
        print(prev_duration, next_duration, prev_event, next_event)
        print((prev_end and utils.todatetime(prev_end) + datetime.timedelta(seconds=prev_duration) >= utils.todatetime(start)), (next_end and utils.todatetime(next_end) + datetime.timedelta(seconds=next_duration) >= utils.todatetime(end)))
        return True
    return False


def fetch_prev_next_event(stream_id, start, end):
    prev_event, next_event = None, None
    obj = EventLogsModel.objects
    prev_events = obj.filter(start__lte=start,
                             stream_id=stream_id).order_by('-start')
    next_events = obj.filter(start__gte=start,
                             stream_id=stream_id).order_by('start')
    if next_events:
        next_event = next_events.values()[0]
    if prev_events:
        prev_event = prev_events.values()[0]
    return (prev_event, next_event)


def estimated_game_finish(game_id):
    """Calculates the estimated maximum time of game to be finished based on:
       -ball type (90,30,etc)
       -call delay (in seconds)
       -BUFFER (optional for added lag)
       returns total seconds
     """
    game_info = utils.get_game_details(game_id)
    if 'error' in game_info:
        print('Nishant----', game_info)
        return 0
    estimated_time = game_info['call_delay'] * game_info['bingo_type'] + BUFFER
    return estimated_time
