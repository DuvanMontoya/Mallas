from django.contrib import admin

from .models import CreditAllocation, DegreeAuditResult, DegreeAuditRun

admin.site.register([DegreeAuditRun, DegreeAuditResult, CreditAllocation])
