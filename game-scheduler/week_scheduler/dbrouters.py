# -*- coding: utf-8 -*-
"""
@author: npatel
Decription: Database model for calendar events
"""
from week_scheduler.models import HistoryModel, UserLogging


class HistoryLog(object):

    def db_for_read(self, model, **hints):
        """ reading HistoryModel from logging """
        if model == HistoryModel or model == UserLogging:
            return 'logging'
        return None

    def db_for_write(self, model, **hints):
        """ writing HistoryModel to logging """
        if model == HistoryModel or model == UserLogging:
            return 'logging'
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """Determine if relationship is allowed between two objects."""

        # Allow any relation between two models that are both in the Example app.
        if obj1._meta.app_label == 'week_scheduler' and obj2._meta.app_label == 'week_scheduler':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that the Example app's models get created on the right database."""
        if app_label == 'week_scheduler':
            # The Example app should be migrated only on the example_db database.
            return db == 'logging'
        elif db == 'logging':
            # Ensure that all other apps don't get migrated on the example_db database.
            return False

        # No opinion for all other scenarios
        return None
