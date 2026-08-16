from django.contrib import admin

from .models import Evidence, NormativeDocument, NormRelation, SourceSnapshot

admin.site.register([NormativeDocument, SourceSnapshot, Evidence, NormRelation])
