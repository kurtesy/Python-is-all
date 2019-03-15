# -*- coding: utf-8 -*-
"""
@author: npatel
Decription: Database model for calendar events
"""
from django.db import models


class UserLogging(models.Model):
    event_id = models.CharField(max_length=10, primary_key=True)
    user_id = models.TextField(null=False)
    approval_id = models.IntegerField(null=True)
    action = models.TextField(null=False)
    previous_data = models.TextField(null=False)
    new_data = models.TextField(null=True)

    class Meta:
        db_table = 'user_activity'
        app_label = 'week_scheduler'
        managed = True


class ScheduleModel(models.Model):
    event_id = models.CharField(max_length=10, primary_key=True)
    game_id = models.IntegerField()
    stream_id = models.IntegerField()
    game_start_time = models.DateTimeField()
    game_end_time = models.DateTimeField()
    linked_room = models.IntegerField()
    context = models.TextField()
    status = models.TextField()
    creation_time = models.DateTimeField()
    last_updated = models.DateTimeField()
    duration = models.IntegerField()

    class Meta:
        db_table = 'bingo_schedule_new'
        app_label = 'week_scheduler'
        managed = True


class EventLogsModel(models.Model):
    event_id = models.CharField(max_length=10, primary_key=True)
    stream_id = models.IntegerField()
    title = models.TextField()
    start = models.TextField()
    end = models.TextField()
    dow = models.TextField()
    user_id = models.TextField(null=False)
    approval_id = models.IntegerField(null=True)
    status = models.TextField()

    class Meta:
        db_table = 'event_logs'
        app_label = 'week_scheduler'
        managed = True


class HistoryModel(models.Model):
    approval_id = models.IntegerField(null=False)
    user_id = models.TextField(null=False)
    data = models.TextField(null=False)

    class Meta:
        db_table = 'history'
        app_label = 'week_scheduler'
        managed = True
