from django.contrib import admin

from .models import PlannedCourse, PlanningPreference, PlanScenario

admin.site.register([PlanScenario, PlannedCourse, PlanningPreference])
