# -*- coding: utf-8 -*-
"""
@author: npatel
Decription: Database model for calendar events
"""

import json
import datetime
import math
import csv
import os
from traceback import format_exc
from wsgiref.util import FileWrapper
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db import connections
from django.db import IntegrityError
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import isodate
from week_scheduler import utils, validation
from .models import ScheduleModel, EventLogsModel, UserLogging, HistoryModel


APPROVAL_ID = 1
WEEKDAY_MAPPING = {'Monday': 0,
                   'Tuesday': 1,
                   'Wednesday': 2,
                   'Thursday': 3,
                   'Friday': 4,
                   'Saturday': 5,
                   'Sunday': 6,
                   }
COLUMNS = """game_id, stream_id, game_start_time, game_end_time, gap_duration,
            status, duration, linked_room, next_event, context, last_updated,
            creation_time"""

CLIPBOARD = []


def week_calendar(request, stream=1):
    """Renders the main home page"""
    print(request.session.session_key)
    return render(request, 'fullcalendar.html',
                  {'stream_list': utils.get_streams(), 'stream': stream,
                   'approval_list': utils.get_approval_list()})


@csrf_exempt
def upload_csv(request):
    """Driver function to Upload scheduling data."""
    data = request.FILES.dict()
    if request.method != "POST":
        response = HttpResponseRedirect('/scheduler/week_calendar/')
    try:
        csv_file = data["csv_file"]
        lines = [line.decode('utf-8')
                 for line in csv_file.open('rb').readlines()]
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            response = HttpResponseRedirect('/scheduler/week_calendar/')
        # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request, "Uploaded file is too big (%.2f MB)."
                           % (csv_file.size/(1000*1000),))
            response = HttpResponseRedirect('/scheduler/week_calendar/')

        """Data validation and processing."""
        file_data = list(csv.DictReader(lines))
        error_rows = validation.validate_csv(file_data)
        if error_rows:
            messages.error(request,
                           "Check Data issues in CSV " + str(error_rows))
            response = HttpResponseRedirect('/scheduler/week_calendar/')
        event_process = csv_upload_process_events(request, file_data)
        if event_process:
            event_list = [event['event_id'] for event in event_process[0]]
            response = render(request, 'conflicts_errors.html',
                              {'conflicts': event_process[0],
                               'current_events': event_process[1],
                               'event_list': event_list})
            print('Nishant------------', event_process)
            return response

        response = HttpResponseRedirect('/scheduler/week_calendar/')
    except Exception as error:
        messages.error(request,
                       "Unable to upload file. " + str(error) + format_exc())
        print(format_exc())
        return HttpResponseRedirect('/scheduler/week_calendar/')
    return response


def reset_events():
    """View to Refresh the page."""
    return HttpResponseRedirect('/scheduler/week_calendar/')


def csv_upload_process_events(request, file_data):
    """Add the events as per the data in the csv uploaded."""
    user = request.user.username
    try:
        next_event = utils.next_event_id()
        conflicts = []
        current_events = []
        ctr = 1
        for row in file_data:
            ctr += 1
            game_id = row['game_id']
            stream_id = row['stream_id']
            if not stream_id:
                continue
            linked_room = row['linked_room']
            room = ' - '.join([stream_id,
                               utils.get_stream_details(stream_id)['stream_name']])
                
            if linked_room:
                game = ' - '.join(['Linked to', linked_room,
                                   utils.get_stream_details(linked_room)['stream_name']])
                row['linked_room'] = ' - '.join([linked_room,
                                          utils.get_stream_details(linked_room)['stream_name']])
            else:
                linked_room = '0'
                game_info = utils.get_game_details(game_id)
                if 'error' in game_info:
                    print(game_info)
                    continue
                game = ' - '.join([game_id, game_info['game_name']])
                row['linked_room'] = 'None'
            title = '|'.join([room, game])
            row['stream_id'] = room
            row['game_id'] = game
            start = row['start_time'].replace('"', '')
            end = row['end_time'].replace('"', '')
            event_id = '_fc' + str(next_event)
            if row['dow']:
                dow = json.loads(row['dow'])
                print(dow, type(dow))
                _conflicts = handle_events(row, game_id, stream_id, dow,
                                           start, end, user, csv=True)
                conflicts.extend(_conflicts)
            else:
                event_logs(stream_id, event_id, title, start, end, user)
                response = process_schedule_data(event_id, game_id,
                                                 stream_id,
                                                 start,
                                                 end,
                                                 linked_room, ctr)
                if response:
                    current_events.append([event_id, game_id, stream_id,
                                           utils.todatetime(start),
                                           utils.todatetime(end),
                                           linked_room])
                    conflicts.append(response)
            next_event += 1
        if conflicts:
            print('Nishant----------', conflicts)
            return (conflicts, current_events)
        return None
    except Exception as error:
        print('Nishant----------', row, format_exc())
        raise Exception(error)


@csrf_exempt
@login_required(login_url='/accounts/login/')
def get_events(request):
    """View to add data of the events created on the page."""
    if request.method == 'POST':
        event_data = json.loads(request.POST.get('the_post'))
        details = utils.extract_info(event_data['title'])
        stream = details['stream']
        stream_id = int(stream.split('-')[0].strip())
        user = request.user.username
        """Validate Event creation"""
        result = validation.consecutive_events(stream_id, event_data['start'],
                                               event_data['end'])
        print('OKKKK', stream_id, event_data['start'],
              event_data['end'], result)
        if result:
            return JsonResponse({'message': 'Event conflicting with prev/next event play time.'},
                                safe=False)
        next_event = utils.next_event_id()
        event_id = '_fc' + str(next_event)
        event_logs(stream, event_id, event_data['title'],
                   event_data['start'].replace('T', ' '),
                   event_data['end'].replace('T', ' '), user)
        return HttpResponse(str(request.POST.get('the_post')))
    return HttpResponse('Not a POST Method')


@csrf_exempt
@login_required(login_url='/accounts/login/')
def remove_event(request):
    """View to remove data of the events created on the page."""
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        print(event_id)
        del_row = EventLogsModel.objects.filter(event_id=event_id)
        user_log(request, del_row.values(), [], 'delete')
        del_row.delete()
        ScheduleModel.objects.filter(event_id=event_id).delete()
        return HttpResponse(str(request.POST.get('event_id')))
    return HttpResponse('Not a POST Method')


@csrf_exempt
def return_events(request):
    """View to render events previously created."""
    stream_id = int(request.POST.get('stream_id').split('-')[0].strip())
    # events = list(EventLogsModel.objects.filter(stream_id=
    # stream_id).exclude(title__contains='No Game Configured').values())
    events = list(EventLogsModel.objects.filter(stream_id=
                                                  stream_id).values())
    events = utils.add_color(events)
    return JsonResponse(events, safe=False)


@csrf_exempt
@login_required(login_url='/accounts/login/')
def click_event(request):
    """View to redirect to scheduling_form page to configure the schedule."""
    if request.method == 'POST':
        click_data = request.POST.dict()
        _id = click_data['_id']
        title = click_data['title']
        details = utils.extract_info(title)
        ball_type = utils.get_ball_type(details['stream_id'])
        dow = []
        print(_id)
        existing_game = list(EventLogsModel.objects.filter(event_id=
                                                           _id).values())
        if existing_game:
            game = existing_game[0]
            dow = json.loads(game['dow'])
        context = {'game_list': utils.get_games(ball_type),
                   'stream': details['stream'],
                   'stream_list': utils.get_streams(),
                   'minute_range': list(range(0, 60)),
                   'dow': dow}
        event_details = {'event_id': _id,
                         'start': click_data['start'],
                         'end': click_data['end'],
                         }
        if 'No Game Configured' not in title:
            event_details.update({'stream': details['stream'],
                                  'game': details['game']})
        if 'Linked to' in title:
            event_details.update({'stream': details['stream'],
                                  'linked_room': details['game']})
        context.update(event_details)
        return render(request, 'scheduling_form.html', context)
    return HttpResponseRedirect('/scheduler/week_calendar/')


@csrf_exempt
@login_required(login_url='/accounts/login/')
def drop_event(request):
    """View to drag & drop event on the page."""
    if request.method == 'POST':
        drop_data = request.POST.dict()
        delta = isodate.parse_duration(drop_data['delta'])
        event_id = drop_data['event_id']
        new_start = drop_data['new_start']
        new_end = drop_data['new_end']
        start = (utils.todatetime(new_start) - delta).strftime("%Y-%m-%d %H:%M")
        end = (utils.todatetime(new_end) - delta).strftime("%Y-%m-%d %H:%M")
        utils.update_event_log(event_id, '', '', '', start, end, [], new_start,
                               new_end)
        user_log(request, {'event_id': event_id, 'start': start, 'end': end},
                 {'event_id': event_id, 'new_start': new_start,
                  'new_end': new_end}, 'dragndrop')
        return JsonResponse(drop_data, safe=False)
    return HttpResponse('Not a POST Method')


@csrf_exempt
@login_required(login_url='/accounts/login/')
def resize_event(request):
    """View to resize an event created on the page."""
    if request.method == 'POST':
        drop_data = request.POST.dict()
        delta = isodate.parse_duration(drop_data['delta'])
        event_id = drop_data['event_id']
        new_start = drop_data['new_start']
        new_end = drop_data['new_end']
        end = (utils.todatetime(new_end) - delta).strftime("%Y-%m-%d %H:%M")
        utils.update_event_log(event_id, '', '', '', new_start, end, [],
                               new_start, new_end)
        user_log(request, {'event_id': event_id, 'start': new_start,
                           'end': end},
                 {'event_id': event_id, 'new_start': new_start,
                  'new_end': new_end}, 'resize')
        return JsonResponse(drop_data, safe=False)
    return HttpResponse('Not a POST Method')


@csrf_exempt
def copy_event(request):
    """View to clipboard an events created on the page."""
    if request.method == 'POST':
        copy_data = request.POST.dict()
        return JsonResponse(copy_data, safe=False)
    return HttpResponse('Not a POST Method')


@csrf_exempt
def paste_event(request):
    """View to paste previously copied data created on the page."""
    if request.method == 'POST':
        paste_data = request.POST.dict()
        return JsonResponse(paste_data, safe=False)
    return HttpResponse('Not a POST Method')


@csrf_exempt
def single_event_object(request):
    """View to render popup data for game details on the page."""
    if request.method == 'POST':
        event_data = request.POST.dict()
        stream_id = event_data['stream_id']
        event_id = event_data['event_id']
        event = EventLogsModel.objects.filter(stream_id=stream_id,
                                              event_id=event_id).values()
        return JsonResponse(list(event), safe=False)
    return HttpResponse('Not a POST Method')


def scheduling_form(request):
    """View to render and pass scheduling form data from home page."""
    context = {'game_list': utils.get_games(),
               'stream_list': utils.get_streams(),
               'minute_range': list(range(0, 60))}
    return render(request, 'scheduling_form.html', context)


def schedule_game(request):
    """Driver to retrieve and process the game scheduled."""
    if request.method == 'GET':
        game_data = request.GET.dict()
        stream_id = int(game_data['stream_id'].split('-')[0].strip())
        game_id = int(game_data['game_id'].split('-')[0].strip())
        user = request.user.username
        if stream_id and game_id:
            event_start_time = game_data['start_datetimepicker']
            event_end_time = game_data['end_datetimepicker']
            days_of_week = request.GET.getlist('dow')
            game_data['limit'] = game_data['limit_datetimepicker']
            conflicts = handle_events(game_data, game_id, stream_id, days_of_week,
                                      event_start_time, event_end_time, user)
            return HttpResponseRedirect('/scheduler/week_calendar/')

    return HttpResponseRedirect('/scheduler/week_calendar/')


def handle_events(game_data, game_id, stream_id, days_of_week,
                  event_start_time, event_end_time, user, csv=False):
    event_start_time = utils.todatetime(event_start_time)
    event_end_time = utils.todatetime(event_end_time)
    limit = game_data['limit']
    linked_room = game_data['linked_room']
    conflicts = []
    if linked_room == 'None':
        linked_room = '0'
        linked_room_id = 0
    else:
        linked_room_id = int(linked_room.split(' - ')[0])

    if limit:
        limit = utils.todatetime(limit.replace('"', ''))
    if days_of_week and not limit:
        limit = event_start_time + datetime.timedelta(days=7)
    if not days_of_week and not limit:
        limit = datetime.datetime(1970, 1, 1)

    game_times = game_time_generator(event_start_time,
                                     event_end_time,
                                     days_of_week, limit)
    print(game_times)
    next_event = utils.next_event_id()
    for game_start, game_end in game_times:
        event_id = '_fc' + str(next_event)
        event_logs(game_data['stream_id'], event_id, '',
                   game_start.strftime("%Y-%m-%d %H:%M"),
                   game_end.strftime("%Y-%m-%d %H:%M"),
                   user)
        response = process_schedule_data(event_id, game_id, stream_id, game_start,
                                         game_end, linked_room_id)
        if response:
            conflicts.append(response)
        if not csv and (game_data['start'] != game_data['start_datetimepicker']
                        or game_data['end'] != game_data['end_datetimepicker']):
            utils.update_event_log(event_id, game_data['stream_id'],
                                   game_data['game_id'],
                                   linked_room,
                                   game_data['start'],
                                   game_data['end'],
                                   days_of_week,
                                   game_data['start_datetimepicker'],
                                   game_data['end_datetimepicker'])
        else:
            utils.update_event_log(event_id, game_data['stream_id'],
                                   game_data['game_id'],
                                   linked_room,
                                   game_start.strftime("%Y-%m-%d %H:%M"),
                                   game_end.strftime("%Y-%m-%d %H:%M"),
                                   days_of_week)
        next_event += 1
    return conflicts


def process_schedule_data(event_id, game_id, stream_id, game_start, game_end,
                          linked_room_id, ctr=None, override=False):
    """Insert the data for the configured schedule in bingo_schedule_new"""
    current_time = datetime.datetime.today()
    """Check for clashing event"""
    try:
        if not override:
            conflict = conflict_event(game_start, stream_id, ctr)
            if conflict:
                return conflict
        """ORM Insert"""
        post = ScheduleModel()
        post.event_id = event_id
        post.game_id = game_id if int(linked_room_id) == 0 else -1
        post.stream_id = stream_id
        post.game_start_time = game_start
        post.game_end_time = game_end
        post.duration = int((game_end - game_start).seconds/60)
        post.linked_room = linked_room_id
        post.status = 'pending'
        post.creation_time = current_time
        post.last_updated = current_time
        post.save()
        return None
    except Exception:
        return format_exc()


def show_data():
    """Test function to show config data"""
    cur = connections['default'].cursor()
    cur.execute("""SELECT *
                  FROM gms.bingo_schedule_new
                  ORDER BY game_start_time
                  """)
    columns = [column[0] for column in cur.description]
    results = []
    for row in cur.fetchall():
        results.append(dict(zip(columns, row)))


def game_time_generator(start_time, end_time, days_of_week, limit):
    """Returns generator object with game times between start and end time"""
    game_times = []
    start_weekday = start_time.weekday() + 1
    limit_weeks = 0
    if start_time < limit:
        limit_weeks = math.ceil(((limit - start_time).days/7.0))

    """Current week game time."""
    game_times.append([start_time, end_time])

    """Future weeks game time."""
    if days_of_week:
        for week in range(1, limit_weeks+1):
            for day in days_of_week:
                day = int(day)
                print(day, week, days_of_week)
                day_count = (day-start_weekday) + 7*week
                weekly_start_time = start_time +\
                    datetime.timedelta(days=day_count)
                weekly_end_time = end_time +\
                    datetime.timedelta(days=day_count)
                game_times.append([weekly_start_time, weekly_end_time])
    return game_times


def conflict_event(game_start_time, stream_id, ctr):
    """Validates the overlapping events"""
    ex_cols = ['context', 'creation_time', 'duration']
    conn = connections['default']
    cur = conn.cursor()
    error = None
#    print("""SELECT *
#                  FROM gms.bingo_schedule_new
#                  WHERE game_start_time <= '%s' and '%s' < game_end_time
#                  AND stream_id = %s
#                  ORDER BY game_start_time""" %
#              (game_start_time, game_start_time, stream_id))
    cur.execute("""SELECT *
                  FROM gms.bingo_schedule_new
                  WHERE game_start_time <= '%s' and '%s' < game_end_time
                  AND stream_id = %s
                  ORDER BY game_start_time""" %
                (game_start_time, game_start_time, stream_id))
    conflict_row = cur.fetchone()
    # print(conflict_row)
    if not conflict_row:
        return None
    conflict_row = map(lambda x: str(x), conflict_row)
    columns = [column[0] for column in cur.description]
    if conflict_row:
        error = dict(zip(columns, conflict_row))
        error = {key: val for key, val in error.items() if key not in ex_cols}
        error.update({'conflicting_row': ctr})
    return error


def event_logs(stream, event_id, title, start, end, user):
    """ORM Insert"""
    print(stream, event_id, title, start, end, user)
    stream_id = int(stream.split('-')[0].strip())
    start_times = list(EventLogsModel.objects.values_list('start',
                                                          flat=True))
    end_times = list(EventLogsModel.objects.values_list('end', flat=True))
    stream_ids = list(EventLogsModel.objects.values_list('stream_id',
                                                         flat=True))
    for startt, endt, _stream in zip(start_times, end_times, stream_ids):
        if startt == start and endt == end and _stream == stream_id:
            rows = EventLogsModel.objects.filter(start=startt, end=endt,
                                                 stream_id=_stream)
            print('Del-------', rows.values())
            rows.delete()
    try:
        event_log = EventLogsModel()
        event_log.stream_id = stream_id
        event_log.event_id = event_id
        event_log.title = title
        event_log.start = start.replace('T', ' ')
        event_log.end = end.replace('T', ' ')
        event_log.dow = '[]'
        event_log.user_id = user
        event_log.approval_id = None
        event_log.status = 'open'
        event_log.save()
    except IntegrityError:
        return


@csrf_exempt
def get_prebuy_stats(request):
    """View to render prebuy stats in popover the event."""
    try:
        params = request.POST.dict()
        title, end = params['title'], params['end']
        stream_id = utils.extract_info(title)['stream_id']
        end = (utils.todatetime(end) -
               datetime.datetime(1970, 1, 1)).total_seconds()
        prebuy_stats = {}
        conn = connections['default']
        cur = conn.cursor()
        cur.execute("""SELECT status,
                            count(distinct account_id) players,
                            sum(no_of_cards * card_cost) as total_wagering
                     FROM gms.prebuy_new
                     WHERE room_id = %s
                       AND game_start_time = %s group by status
                  """ % (stream_id, end))
        rows = cur.fetchall()
        for row in rows:
            prebuy_stats[row[0]] = {'players': row[1],
                                    'total_wagering': row[2]}
        if not prebuy_stats:
            prebuy_stats = 'No prebuy records.'
        return JsonResponse(prebuy_stats, safe=False)
    except KeyError:
        return JsonResponse({}, safe=False)


@csrf_exempt
def bulk_delete(request):
    """View to delete multiple event based on the datetime range."""
    del_data = request.POST.dict()
    stream_id = int(del_data['stream'].split(' - ')[0])
    EventLogsModel.objects.filter(start__range=(del_data['from_date'],
                                                del_data['to_date']),
                                  stream_id=stream_id).delete()
    ScheduleModel.objects.filter(game_start_time__range=(del_data['from_date'],
                                                         del_data['to_date']),
                                 stream_id=stream_id).delete()
    messages.info(request, 'Events deleted for range %s' % del_data)
    return HttpResponseRedirect('/scheduler/week_calendar/')


@csrf_exempt
def download_csv(request):
    """View to send a file to client as per the download request option."""
    try:
        download_req = request.POST.dict()
        # messages.info(request, download_req)
        download_type = download_req['download_op']
        stream_id = int(download_req['down_stream_id'].split(' - ')[0])
        rows = []
        file_path = os.path.join(settings.PROJECT_PATH,
                                 settings.DOWNLOAD_FILE_NAME)
        if download_type == 'month':
            start, end = utils.range_of_month(download_req['month_year'])
            suffix = download_req['month_year']
        if download_type == 'week':
            start, end = utils.range_of_week(download_req['week_year'])
            suffix = download_req['week_year']
        if download_type == 'day':
            start, end = utils.range_of_day(download_req['download_date'])
            suffix = download_req['download_date']
        if download_type == 'custom':
            start = download_req['custom_from_date']
            end = download_req['custom_to_date']
            suffix = '_'.join([download_req['custom_from_date'],
                               download_req['custom_to_date']])

        rows = utils.extract_schedule_data(stream_id, start, end)
        # messages.info(request, (str(start), str(end), rows))
        header = ['stream_id', 'game_id', 'start_time', 'end_time',
                  'linked_room', 'dow', 'limit']

        with open(file_path, 'w', newline='') as fhdl:
            writer = csv.DictWriter(fhdl, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        return send_file(file_path, suffix)
    except Exception as error:
        messages.error(request, 'File cannot be downloaded - ' + error)
        pass

    return HttpResponseRedirect('/scheduler/week_calendar/')


def send_file(filename, suffix=''):
    """
    Send a file through Django without loading the whole file into
    memory at once. The FileWrapper will turn the file object into an
    iterator for chunks of 8KB.
    """
    wrapper = FileWrapper(open(filename, 'r'))
    content_type = 'text/csv'
    response = HttpResponse(wrapper, content_type=content_type)
    response['Content-Disposition'] = ('attachment; filename=%s_%s' %
                                       (suffix, os.path.basename(filename)))
    return response


@csrf_exempt
def validation_form(request):
    """View to render validation page to check and verify the conflicts"""
    resolved_data = request.POST.dict()
    print(resolved_data)
    current_events = json.loads(resolved_data['current_events'])
    override = json.loads(resolved_data['override_list'])
    for event in current_events:
        event_id = event[0]
        if event_id in override:
            EventLogsModel.objects.filter(event_id=event_id).delete()
            this_event = event.append('True')
            process_schedule_data(*this_event)
    return render(request, 'conflicts_errors.html')


@csrf_exempt
@login_required(login_url='/accounts/login/')
def approval_request(request):
    """View to process the approval submission for created events in current
       session.
       Session continues of the approval submission is not made."""
    global APPROVAL_ID
    APPROVAL_ID += 1
    user = request.user.username
    utils.update_approval_log(user, APPROVAL_ID)
    return HttpResponseRedirect('/scheduler/week_calendar/')


@csrf_exempt
@login_required(login_url='/accounts/login/')
def grant_approval(request):
    """View to update data for the approved events by the superuser."""
    approval_id = request.POST.get('approval_id')
    user = request.user.username
    data = utils.update_approval_log(user, approval_id, True)
    history = HistoryModel()
    history.approval_id = approval_id
    history.data = data.object.values()
    history.user_id = user
    return HttpResponseRedirect('/scheduler/week_calendar/')


def user_log(request, prev_data, next_data, action):
    """ORM Insert"""
    log = UserLogging()
    event = prev_data[0]
    log.approval_id = event['approval_id']
    log.action = action
    log.event_id = event['event_id']
    log.new_data = str(next_data)
    log.previous_data = str(prev_data)
    log.user_id = request.user.username
    log.save(using='logging')
