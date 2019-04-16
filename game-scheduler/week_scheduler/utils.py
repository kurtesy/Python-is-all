# -*- coding: utf-8 -*-
"""
@author: npatel
Decription: Database model for calendar events
"""
import datetime
import json
from dateutil import parser
from django.db import connections
from dateutil.relativedelta import relativedelta
from .models import EventLogsModel, ScheduleModel


def add_color(events):
    """Adds the color attribute to variou events to be rendered."""
    new_events = []
    status_color = {'open': 'LemonChiffon',
                    'pending': 'silver',
                    'approved': 'LightGreen',
                    'completed': 'OrangeRed'}
    # rgb = lambda: random.randint(128, 255)
    for event in events:
        if 'Linked to' in event['title']:
            event.update({'textColor': 'navy'})
            event.update({'borderColor': 'navy'})
        event.update({'color': status_color[event['status']]})
        new_events.append(event)
    return new_events


def extract_schedule_data(stream_id, start, end):
    """Returns the game information from the event logs data."""
    data = []
    obj = EventLogsModel.objects
    rows = obj.filter(start__gte=start,
                      end__lt=end,
                      stream_id=stream_id).order_by('start').values('stream_id',
                                                                    'title',
                                                                    'start',
                                                                    'end',
                                                                    'dow')
    for row in rows:
        new_row = {'stream_id': row['stream_id']}
        game_info = extract_info(row['title'])
        new_row['game_id'] = game_info['game_id']
        new_row['start_time'] = '"' + row['start'] + '"'
        new_row['end_time'] = '"' + row['end'] + '"'
        if game_info['linked_room']:
            new_row['linked_room'] = game_info['linked_room'][0]
        else:
            new_row['linked_room'] = game_info['linked_room']
        new_row['dow'] = row['dow']
        data.append(new_row)
    return data


def get_ball_type(stream_id):
    """Returns ball type of selecetd stream."""
    conn = connections['default']
    cur = conn.cursor()
    cur.execute("""SELECT game_type
                  FROM gms.streams
                 WHERE stream_id = %s
              """ % (stream_id,))
    rows = cur.fetchone()
    return rows[0]


def get_games(ball_type=None):
    """Returns the steeam list format as {stream_id} - {stream_name}"""
    game_data = []
    conn = connections['default']
    cur = conn.cursor()
    cur.execute("""SELECT game_id, game_name
                  FROM gms.games
                 WHERE bingo_type=%s
              """ % (ball_type,))
    rows = cur.fetchall()
    print('oKKKKKK', rows[0:4])
    for row in rows:
        game_data.append(' - '.join(map(str, row)))
    return game_data


def get_next_approval_id():
    """Returns the incremented last approval id added to the event logs."""
    args = EventLogsModel.objects
    # Calculates the maximum out of the already-retrieved objects
    approval_ids = list(args.values_list('approval', flat=True))
    if not approval_ids:
        last_id = 0
    else:
        last_id = max(approval_ids)
    return last_id + 1


def get_streams():
    """Returns the stream list format as {stream_id} - {stream_name}"""
    stream_data = []
    conn = connections['default']
    cur = conn.cursor()
    cur.execute("""SELECT stream_id, stream_name
                  FROM gms.streams
              """)
    rows = cur.fetchall()
    for row in rows:
        stream_data.append(' - '.join(map(str, row)))
    return stream_data


def get_stream_details(stream_id):
    """Returns the stream name and id from game.streams."""
    conn = connections['default']
    cur = conn.cursor()
    cur.execute("""SELECT stream_id,
                        stream_name
                  FROM gms.streams
                  WHERE stream_id = %s
              """ % (stream_id,))
    row = cur.fetchone()
    if not row:
        return 'Stream not found in DB'
    return {'stream_id': row[0],
            'stream_name': row[1], }


def next_event_id():
    """Returns the incremented last event id added to the event logs."""
    args = EventLogsModel.objects
    # Calculates the maximum out of the already-retrieved objects
    event_ids = list(args.values_list('event_id', flat=True))
    event_ids = list(map(lambda x: int(x.replace('_fc', '')), event_ids))
    if not event_ids:
        last_event = 0
    else:
        last_event = max(event_ids)
    event_num = last_event + 1
    return event_num


def get_game_details(game_id):
    """Returns the game details from game.games table."""
    conn = connections['default']
    cur = conn.cursor()
    cur.execute("""SELECT game_id,
                        game_name,
                        call_delay,
                        bingo_type
                  FROM gms.games
                  WHERE game_id = %s
              """ % (game_id,))
    row = cur.fetchone()
    if not row:
        return {'error': 'Game not found in DB'}
    return {'game_id': row[0],
            'game_name': row[1],
            'call_delay': row[2],
            'bingo_type': row[3], }


def range_of_month(month_year):
    """Returns the month range of from and
       to download schedule."""
    start = datetime.datetime.strptime(month_year, '%Y-%m')
    end = start + relativedelta(months=1) - datetime.timedelta(days=1)
    return (start, end)


def range_of_week(week_year):
    """Returns the week range of from and
       to download schedule."""
    end = datetime.datetime.strptime(week_year + '-1', "%Y-W%W-%w")
    start = end - datetime.timedelta(days=7)
    return (start, end)


def range_of_day(date):
    """Returns the datetime range of from and
       to download schedule."""
    start = datetime.datetime.strptime(date, "%Y-%m-%d")
    end = start + datetime.timedelta(hours=24)
    return (start, end)


def extract_info(title):
    """Extract the stream id, stream name,
        game id and game name.
    """
    linked_room = None
    stream = title.split('|')[0]
    stream_id = int(stream.split('-')[0].strip())
    game = title.split('|')[1]
    if 'Linked to' in game:
        linked_room = game.split(' - ')[1:]
        game_id = -1
    elif 'No Game Configured' in game:
        game_id = -1
    else:
        game_id = int(game.split('-')[0].strip())
    return {'stream_id': stream_id,
            'game_id': game_id,
            'stream': stream,
            'game': game,
            'linked_room': linked_room, }


def get_approval_list(is_super=None, user=None):
    """Fetch the approval id from the event logs in DB."""
    if is_super:
        approval_list = EventLogsModel.objects.values_list('approval_id')
        approval_list = set(map(lambda x: x[0], approval_list))
    else:
        approval_list = EventLogsModel.objects.filter(user_id=user).values_list('approval_id')
    return list(approval_list)


def todatetime(date_str):
    """Cleans and converts the string date-time to python datetime object."""
    try:
        return parser.parse(date_str)
    except Exception:
        return None


def update_event_log(event_id, stream, game, linked_room, start, end, dow=None,
                     new_start=None, new_end=None):
    """Update the event logs in case of following events:
        - Resize: Increase the end time
        - Drag $ Drop: Modify the start and end time
        - Handles if the start and end is modified in scheduling_form
        - Updates if a linked event is configured"""
    print(event_id)
    rows = EventLogsModel.objects.filter(start=start, end=end)
    # print(rows.values())
    if new_start and new_end:
        rows.update(start=new_start, end=new_end, status='open')
        print(new_start, new_end)
        return
    if new_start and not new_end:
        rows.update(start=new_start, status='open')
    elif new_end:
        rows.update(end=new_end, status='open')
    else:
        if linked_room != '0':
            title = stream + '|Linked to - ' + linked_room
        else:
            title = stream + '|' + game
        rows.update(title=title,
                    start=start,
                    end=end)
    if dow:
        dow = json.dumps(dow)
        rows.update(dow=dow.replace("'", '"'))


def update_approval_log(stream_id, user_id, approval_id, superuser=False,
                        action='approve', event_id=None):
    """Update the approval status, user and approval id for
        - Superuser who approves the request
        - Other user who submites the request."""
    if superuser:
        rows = EventLogsModel.objects.filter(stream_id=stream_id,
                                             approval_id=approval_id)
        print(rows.values())
        if action == 'approve':
            rows.update(status='approved')
            event_ids = rows.values_list('event_id')
            update_game_status(event_ids)
            return rows
        if action == 'delete':
            rows.delete()
            event_ids = rows.values_list('event_id')
            ScheduleModel.objects.filter(event_id__in=event_ids).delete()
            return
    else:
        if action == 'delete':
            rows = EventLogsModel.objects.filter(stream_id=stream_id,
                                                 event_id=event_id)
            rows.update(status='pending', approval_id=next_approval_id)
    pending_rows = EventLogsModel.objects.filter(stream_id=stream_id,
                                                 user_id=user_id,
                                                 approval_id__isnull=False,
                                                 status='pending')
    rows = EventLogsModel.objects.filter(stream_id=stream_id, user_id=user_id,
                                         approval_id__isnull=True)
    if len(pending_rows) != 0 and len(rows) == 0:
        return 'pending approval'
    if len(rows) == 0:
        return 'no games created'
    rows.update(approval_id=approval_id, status='pending')
    return rows


def update_game_status(event_ids, status='active'):
    """Update the game status as per the approval."""
    rows = ScheduleModel.objects.filter(event_id__in=event_ids)
    rows.update(status=status)


def update_approval_status(stream_id, user_id, approval_id, superuser=False):
    """Update the approval status, user and approval id for
        - Superuser who approves the request
        - Other user who submites the request."""
    if superuser:
        rows = EventLogsModel.objects.filter(stream_id=stream_id,
                                             approval_id=approval_id)
        print(rows.values())
        rows.update(status='approved')
        event_ids = rows.values_list('event_id')
        update_game_status(event_ids)
        return rows
    rows = EventLogsModel.objects.filter(stream_id=stream_id, user_id=user_id,
                                         approval_id__isnull=True)
    rows.update(approval_id=approval_id, status='pending')
    return rows


def next_approval_id():
    """Returns the incremented last event id added to the event logs."""
    args = EventLogsModel.objects
    # Calculates the maximum out of the already-retrieved objects
    approval_id = list(filter(lambda x: x, list(args.values_list('approval_id',
                                                                 flat=True))))
    if not approval_id:
        last_approval = 0
    else:
        last_approval = max(approval_id)
    approval_id = last_approval + 1
    return approval_id


def update_on_revoke(stream_id, user):
    rows = EventLogsModel.objects.filter(stream_id=stream_id, user_id=user,
                                         status='pending')
    rows.update(approval_id=None, status='open')
