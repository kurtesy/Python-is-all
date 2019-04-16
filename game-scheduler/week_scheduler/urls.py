# -*- coding: utf-8 -*-

from django.conf.urls import url
from week_scheduler import views

urlpatterns = [
    url(r'^week_calendar/(?P<stream>\d+\s-\s[\w\s]+)', views.week_calendar, name='week_calendar', ),
    url(r'^scheduling_form/$', views.scheduling_form, name='scheduling_form'),
    url(r'^schedule_game/$', views.schedule_game, name='schedule_game'),
    url(r'^get_events/$', views.get_events, name='get_events'),
    url(r'^return_events/$', views.return_events, name='return_events'),
    url(r'^reset_events/$', views.reset_events, name='reset_events'),
    url(r'^click_event/$', views.click_event, name='click_event'),
    url(r'^remove_event/$', views.remove_event, name='remove_event'),
    url(r'^drop_event/$', views.drop_event, name='drop_event'),
    url(r'^resize_event/$', views.resize_event, name='resize_event'),
    url(r'^single_event_object/$', views.single_event_object, name='single_event_object'),
    url(r'^copy_event/$', views.copy_event, name='copy_event'),
    url(r'^paste_event/$', views.paste_event, name='paste_event'),
    url(r'^upload_csv/$', views.upload_csv, name='upload_csv'),
    url(r'^get_stats/$', views.get_stats, name='get_stats'),
    url(r'^bulk_delete/$', views.bulk_delete, name='bulk_delete'),
    url(r'^download_csv/$', views.download_csv, name='download_csv'),
    url(r'^validation_form/$', views.validation_form, name='validation_form'),
    url(r'^approval_request/$', views.approval_request, name='approval_request'),
    url(r'^grant_approval/$', views.grant_approval, name='grant_approval'),
    url(r'^log_view/$', views.log_view, name='log_view'),
]
