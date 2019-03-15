import json
import datetime
import math
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.core.exceptions import ValidationError
from .models import bingo_schedule_new_model, event_logs_model
from django.db import connections
from django.db import IntegrityError
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
# Create your views here.

SUMMARY = []
EVENT_DATA = {}
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


def reset_events(request):
    global EVENT_DATA
    if 'reset' in request.POST:
        EVENT_DATA = {}
    return HttpResponseRedirect('/scheduler/week_calendar/')


@csrf_exempt
def get_events(request):
    if request.method == 'POST':
        event_data = json.loads(request.POST.get('the_post'))
        EVENT_DATA[event_data['_id']] = {
                                         'title': event_data['title'],
                                         'start': event_data['start'],
                                         'end': event_data['end'],}
        event_logs(event_data['_id'], event_data['title'],
                   event_data['start'][:16].replace('T', ' '),
                   event_data['end'][:16].replace('T', ' '))
        return HttpResponse(str(request.POST.get('the_post')))
    return HttpResponse('Not a POST Method')


@csrf_exempt
def remove_event(request):
    if request.method == 'POST':
        start = request.POST.get('start')[:16].replace('T', ' ')
        end = request.POST.get('end')[:16].replace('T', ' ')
        print(start,end)
        event_logs_model.objects.filter(start=start, end=end).delete()
        return HttpResponse(str(request.POST.get('event_id')))
    return HttpResponse('Not a POST Method')


@csrf_exempt
def return_events(request):
    global EVENT_DATA
    events = list(event_logs_model.objects.values())
    EVENT_DATA = {event['event_id']: event for event in events}
    return JsonResponse(events, safe=False)


@csrf_exempt
def click_event(request):
    if request.method == 'POST':
        _id = request.POST.get('_id')
        title = request.POST.get('title')
        context = {'game_list': get_games(),
                   'stream_list': get_streams(),
                   'minute_range': list(range(0, 60))}
        event_details = {'event_id': _id,
                         'starttime': request.POST.get('start')[:16],
                         'endtime': request.POST.get('end')[:16],
                         }
        if title != 'No Game Configured':
            title = title.split('|')
            event_details.update({'stream': title[0],
                                  'game': title[1]})
        context.update(event_details)
        return render(request, 'scheduling_form.html', context)
    return HttpResponseRedirect('/scheduler/week_calendar/')


def scheduling_form(request):
    context = {'game_list': get_games(),
               'stream_list': get_streams(),
               'minute_range': list(range(0, 60))}
    return render(request, 'scheduling_form.html', context)


def schedule_game(request):
    global SUMMARY
    SUMMARY = []
    if request.method == 'GET':
        game_details = request.GET.dict()
        stream_id = int(game_details['stream_id'].split('-')[0].strip())
        game_id = int(game_details['game_id'].split('-')[0].strip())
        if stream_id and game_id:
            event_id = game_details['event_id']
            event_start_time = todatetime(game_details['start_datetimepicker'])
            event_end_time = todatetime(game_details['end_datetimepicker'])
            game_interval = int(game_details['game_interval'])
            gap_interval = int(game_details['gap_interval'])
            days_of_week = request.GET.getlist('dow')
            limit = game_details['limit_datetimepicker']
            linked_room = game_details['linked_room']
            if limit:
                limit = todatetime(limit)
            if days_of_week and not limit:
                limit = event_start_time + datetime.timedelta(days=7)
            if not days_of_week and not limit:
                limit = datetime.datetime(1970, 1, 1)
            game_start_times = game_time_generator(event_start_time,
                                                   event_end_time,
                                                   game_interval, gap_interval,
                                                   days_of_week, limit)
            total_games = len(game_start_times)
            if not event_end_time or event_end_time == event_start_time:
                game_start_times = [event_start_time]
            for ix, game in enumerate(game_start_times):
                last_game = bool(ix + 1 == total_games)
                response = process_schedule_data(game_id, stream_id, game,
                                                 game_interval, linked_room,
                                                 last_game)
                update_event_log(event_id, game_details['stream_id'],
                                 game_details['game_id'],
                                 game_details['start_datetimepicker'].replace('T', ' '),
                                 game_details['end_datetimepicker'].replace('T', ' '),
                                 days_of_week)
                if response:
                    return response
            show_data()
            # return render(request, 'scheduling_form.html')
#            return HttpResponse(json.dumps(SUMMARY, indent=4,
#                                           cls=DjangoJSONEncoder),
#                                content_type="application/json")
            return HttpResponseRedirect('/scheduler/week_calendar/')
        else:
            HttpResponse('Stream and game id is not specified')

    else:
        return HttpResponseRedirect('/scheduler/week_calendar/')


def process_schedule_data(game_id, stream_id, game, game_interval,
                          linked_room, last_game):
    current_time = datetime.datetime.today()
    """Check for clashing event"""
    game_start_time = game[1]
    conflict = conflict_event(game_start_time, stream_id)
    if conflict == 'idle':
        remove_modified_idle_event(game_start_time, stream_id)
    elif conflict:
        return HttpResponse(json.dumps(conflict, indent=4,
                                       cls=DjangoJSONEncoder),
                            content_type="application/json")
    """ORM Insert"""
    post = bingo_schedule_new_model()
    post.game_id = game_id
    post.stream_id = stream_id
    post.game_start_time = game_start_time
    post.game_end_time = game_start_time\
        + datetime.timedelta(minutes=game_interval)
    post.duration = game_interval
    post.linked_room = linked_room
    post.status = 'active'
    post.creation_time = current_time
    post.last_updated = current_time

    post.save()
    calculate_prev_event(game_start_time, post, last_game)
    calculate_next_event(game_start_time, post, last_game)
    return None


def calculate_prev_event(game_start_time, post, last_game):
    conn = connections['default']
    c = conn.cursor()
    c.execute("""SELECT event_id, game_end_time
                  FROM gms.bingo_schedule_new
                  WHERE UNIX_TIMESTAMP(game_start_time)<UNIX_TIMESTAMP('%s')
                      and status='active'
                      and game_id = %s
                      and stream_id = %s
                  ORDER BY UNIX_TIMESTAMP(game_start_time) DESC""" %
              (game_start_time,
               post.game_id, post.stream_id))
    prev_event = c.fetchone()
    if prev_event:
        # print('Prev event', post.game_start_time, game_start_time,
        #      prev_event, post.pk)
        now = datetime.datetime.today().strftime("%Y-%m-%d %H:%M")
        gap_duration = post.game_start_time - prev_event[1]
        gap_duration = int(gap_duration.total_seconds()/60)
        event_id = post.pk
        """Add Game Idle event"""
        if gap_duration > 0:
            c.execute("""INSERT INTO gms.bingo_schedule_new(%s)
                      VALUES (-1, %s, '%s', '%s', %s, 'idle', %s, -1, %s,
                             '', '%s', '%s')""" %
                      (COLUMNS, post.stream_id, prev_event[1],
                       post.game_start_time,
                       gap_duration, gap_duration, event_id, now, now))
            event_id += 1

        """Update the prev game with link to next game"""
        c.execute("""UPDATE gms.bingo_schedule_new
                      SET next_event = %s,
                          last_updated = NOW(),
                          gap_duration = %s
                      WHERE event_id=%s and status='active' """ %
                  (event_id, gap_duration, prev_event[0]))
        conn.commit()
        SUMMARY.extend(['Updated prev event'])
    c.close()
    conn.close()


def calculate_next_event(game_start_time, post, last_game):
    conn = connections['default']
    c = conn.cursor()
    c.execute("""SELECT event_id, game_start_time
                  FROM gms.bingo_schedule_new
                  WHERE UNIX_TIMESTAMP(game_start_time)>UNIX_TIMESTAMP('%s')
                      and status='active'
                      and game_id = %s
                      and stream_id = %s
                  ORDER BY UNIX_TIMESTAMP(game_start_time)""" %
              (game_start_time, post.game_id, post.stream_id))
    next_event = c.fetchone()
    if next_event:
        # print('Next event', post.game_start_time, game_start_time,
        #        next_event, post.pk)
        now = datetime.datetime.today().strftime("%Y-%m-%d %H:%M")
        gap_duration = next_event[1] - post.game_end_time
        gap_duration = int(gap_duration.total_seconds()/60)
        event_id = post.pk
        """Add Game Idle event"""
        if gap_duration > 0 and last_game:
            c.execute("""INSERT INTO gms.bingo_schedule_new(%s)
                      VALUES (-1, %s, '%s', '%s', %s, 'idle', %s, -1, %s,
                             '', '%s', '%s')""" %
                      (COLUMNS, post.stream_id, post.game_end_time,
                       next_event[1],
                       gap_duration, gap_duration, next_event[0], now, now))
        """Update the next game with link to prev game"""
        c.execute("""UPDATE gms.bingo_schedule_new
                      SET next_event = %s,
                          last_updated = NOW(),
                          gap_duration = %s
                      WHERE event_id=%s and status='active' """ %
                  (next_event[0]+3, gap_duration, event_id))
        conn.commit()
        SUMMARY.extend(['Updated next event'])
    c.close()
    conn.close()


def remove_modified_idle_event(game_start_time, stream_id):
    conn = connections['default']
    c = conn.cursor()
    c.execute("""SELECT event_id
                  FROM gms.bingo_schedule_new
                  WHERE game_start_time < '%s'
                      and status='idle'
                      and game_id = %s
                      and stream_id = %s
                  ORDER BY UNIX_TIMESTAMP(game_start_time)""" %
              (game_start_time, -1, stream_id))
    event_id = c.fetchone()
    if event_id:
        """Remove modified idle game"""
        c.execute("""DELETE FROM gms.bingo_schedule_new
                     WHERE event_id=%s""" % (event_id))
        conn.commit()
        c.close()
        conn.close()
        print('remove_modified_idle_event')


def show_data():
    c = connections['default'].cursor()
    c.execute("""SELECT *
                  FROM gms.bingo_schedule_new
                  ORDER BY game_start_time
                  """)
    columns = [column[0] for column in c.description]
    results = []
    for row in c.fetchall():
        results.append(dict(zip(columns, row)))
    SUMMARY.extend(results)


def todatetime(date_str):
    date_str = date_str.replace('T', ' ')
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M')
    except ValueError as error:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except Exception as error:
        return None


def game_time_generator(start_time, end_time, interval, gap, days_of_week,
                        limit):
    """Returns generator object with game times between start and end time"""
    # XXX TODO gap for idle games insertion
    game_start_times = []
    intv = datetime.timedelta(minutes=interval)
    start_weekday = start_time.weekday() + 1
    limit_weeks = 0
    if start_time < limit:
        limit_weeks = math.ceil(((limit - start_time).days/7.0))
    """Future weeks game time."""
    if days_of_week:
        for week in range(0, limit_weeks):
            for day in days_of_week:
                day = int(day)
                if start_weekday <= day:
                    day_count = (day-start_weekday) + 7*week
                    weekly_start_time = start_time +\
                        datetime.timedelta(days=day_count)
                    weekly_end_time = end_time +\
                        datetime.timedelta(days=day_count)
                    while weekly_start_time <= weekly_end_time-intv:
                        game_start_times.append((1, weekly_start_time))
                        weekly_start_time += intv
                        if gap:
                            game_start_times.append((0, weekly_start_time))
                            weekly_start_time += gap
    """Current week game time."""
    while start_time <= end_time-intv:
        game_start_times.append((1, start_time))
        start_time += intv
        if gap:
            game_start_times.append((0, start_time))
            start_time += gap
    return sorted(game_start_times)


def conflict_event(game_start_time, stream_id):
    conn = connections['default']
    c = conn.cursor()
#    print("""SELECT *
#                  FROM gms.bingo_schedule_new
#                  WHERE game_start_time >= '%s'
#                      and game_end_time <= '%s'
#                      and stream_id = %s
#                  ORDER BY game_start_time""" %
#               (game_start_time, game_start_time, stream_id))
    c.execute("""SELECT *
                  FROM gms.bingo_schedule_new
                  WHERE game_start_time <= '%s' and '%s' < game_end_time
                  AND stream_id = %s
                  ORDER BY game_start_time""" %
              (game_start_time, game_start_time, stream_id))
    conflict_row = c.fetchone()
#    print(conflict_row)
    columns = [column[0] for column in c.description]
    if conflict_row and conflict_row[1] == -1:
        return 'idle'
    if conflict_row and conflict_row[1] != -1:
        error = {'message': 'Data already exist for particular time range %s,\
                  please modify or delete the existing event to proceed' %
                 (game_start_time,)}
        error.update(dict(zip(columns, conflict_row)))
        return error


def get_streams():
    stream_data = []
    conn = connections['default']
    c = conn.cursor()
    c.execute("""SELECT stream_id, stream_name
                  FROM gms.streams
              """)
    rows = c.fetchall()
    for row in rows:
        stream_data.append(' - '.join(map(str, row)))
    return stream_data;

def get_games():
    game_data = []
    conn = connections['default']
    c = conn.cursor()
    c.execute("""SELECT game_id, game_name
                  FROM gms.games
              """)
    rows = c.fetchall()
    for row in rows:
        game_data.append(' - '.join(map(str, row)))
    return game_data;


def event_logs(event_id, title, start, end):
    """ORM Insert"""
    start_times = list(event_logs_model.objects.values_list('start', flat=True))
    end_times = list(event_logs_model.objects.values_list('end', flat=True))
    if start in start_times and end in end_times:
        x=event_logs_model.objects.filter(start=start, end=end)
        x.delete()
    try:
        event_logs = event_logs_model()
        event_logs.event_id = event_id
        event_logs.title = title
        event_logs.start = start.replace('T', ' ')
        event_logs.end = end.replace('T', ' ')
        event_logs.save()
    except IntegrityError as e:
        return


def update_event_log(event_id, stream, game, start, end, dow):
#    print(event_id, stream, game, start, end)
    rows = event_logs_model.objects.filter(start=start, end=end)
    if dow:
        dow = list(map(int, dow))
        start = start[-5:]
        end = end[-5:]
    rows.update(title=stream + '|' + game,
                start=start,
                end=end, dow=dow)
