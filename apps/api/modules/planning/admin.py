from django.contrib import admin

from .models import PlannedCourse, PlanningPreference, PlanScenario, ScenarioAuditProjection

admin.site.register([PlanScenario, PlannedCourse, PlanningPreference, ScenarioAuditProjection])
