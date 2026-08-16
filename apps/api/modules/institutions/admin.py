from django.contrib import admin

from .models import Campus, Faculty, Institution, Program

admin.site.register([Institution, Campus, Faculty, Program])
