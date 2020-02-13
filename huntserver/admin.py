from django.contrib import admin
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import FilteredSelectMultiple
from huntserver.widgets import HtmlEditor
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe
from django.template.defaultfilters import truncatechars

# Register your models here.
from . import models


def short_team_name(teamable_object):
    return truncatechars(teamable_object.team.team_name, 50)


short_team_name.short_description = "Team name"


class HintAdmin(admin.ModelAdmin):
    list_display = [short_team_name, 'puzzle', 'request_time', 'has_been_answered']

    def has_been_answered(self, hint):
        return hint.response != ""

    has_been_answered.boolean = True
    has_been_answered.short_description = "Answered?"


class HintUnlockPlanForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(HintUnlockPlanForm, self).__init__(*args, **kwargs)
        self.fields['unlock_parameter'].help_text = ("Exact time: Number of minutes after hunt "
                                                     "start</br>Interval: Number of minutes in the "
                                                     "unlock interval</br> Solves: Number of "
                                                     "puzzles to unlock a hint.")


class HintUnlockPLanInline(admin.TabularInline):
    model = models.HintUnlockPlan
    extra = 2
    form = HintUnlockPlanForm
    fields = ['unlock_type', 'unlock_parameter']
    radio_fields = {"unlock_type": admin.VERTICAL}


class HuntAdminForm(forms.ModelForm):
    model = models.Hunt

    class Meta:
        widgets = {
            'template': HtmlEditor(attrs={'style': 'width: 90%; height: 400px;'}),
        }


class HuntAdmin(admin.ModelAdmin):
    form = HuntAdminForm
    inlines = (HintUnlockPLanInline,)
    fields = ['hunt_name', 'hunt_number', 'is_current_hunt', 'team_size', 'location',
              ('start_date', 'display_start_date'), ('end_date', 'display_end_date'),
              'resource_link', 'points_per_minute', 'extra_data', 'template', 'hint_lockout']
    list_display = ['hunt_name', 'team_size', 'start_date', 'is_current_hunt']


class MessageAdmin(admin.ModelAdmin):
    list_display = [short_team_name, 'short_message']

    def short_message(self, message):
        return truncatechars(message.text, 60)

    short_message.short_description = "Message"


class PersonAdmin(admin.ModelAdmin):
    list_display = ['user_full_name', 'user_username', 'is_shib_acct']
    search_fields = ['user__email', 'user__username', 'user__first_name', 'user__last_name']
    filter_horizontal = ['teams']

    def user_full_name(self, person):
        return person.user.first_name + " " + person.user.last_name

    def user_username(self, person):
        return person.user.username

    user_full_name.short_description = "Name"
    user_username.short_description = "Username"


class PrepuzzleAdminForm(forms.ModelForm):
    class Meta:
        model = models.Prepuzzle
        fields = ['puzzle_name', 'released', 'hunt', 'answer', 'resource_link', 'template',
                  'response_string']
        widgets = {
            'template': HtmlEditor(attrs={'style': 'width: 90%; height: 400px;'}),
        }


class PrepuzzleAdmin(admin.ModelAdmin):
    form = PrepuzzleAdminForm
    list_display = ['puzzle_name', 'hunt', 'released']
    readonly_fields = ('puzzle_url',)

    # Needed to add request to modelAdmin
    def get_queryset(self, request):
        qs = super(PrepuzzleAdmin, self).get_queryset(request)
        self.request = request
        return qs

    def puzzle_url(self, obj):
        puzzle_url_str = "http://" + self.request.get_host() + "/prepuzzle/" + str(obj.pk) + "/"
        html = "<script> function myFunction() { "
        html += "var copyText = document.getElementById('puzzleURL'); "
        html += "copyText.select(); "
        html += "document.execCommand('copy'); } </script>"
        html += "<input style='width: 400px;' type=\"text\""
        html += "value=\"" + puzzle_url_str + "\" id=\"puzzleURL\">"
        html += "<button onclick=\"myFunction()\" type=\"button\">Copy Puzzle URL</button>"
        return mark_safe(html)

    puzzle_url.short_description = 'Puzzle URL: (Not editable)'


class UnlockInline(admin.TabularInline):
    model = models.Puzzle.unlocks.through
    extra = 2
    fk_name = 'to_puzzle'
    verbose_name = "Puzzle that counts towards unlocking this puzzle"
    verbose_name_plural = "Puzzles that count towards this puzzle"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "from_puzzle":
            try:
                parent_obj_id = request.resolver_match.kwargs['object_id']
                puzzle = models.Puzzle.objects.get(id=parent_obj_id)
                query = models.Puzzle.objects.filter(hunt=puzzle.hunt)
                kwargs["queryset"] = query.order_by('puzzle_id')
            except IndexError:
                pass
        return super(UnlockInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ResponseInline(admin.TabularInline):
    model = models.Response
    extra = 1


class PuzzleAdminForm(forms.ModelForm):
    reverse_unlocks = forms.ModelMultipleChoiceField(
        models.Puzzle.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Puzzle', False),
        required=False,
        label="Puzzles that count towards this puzzle"
    )

    def __init__(self, *args, **kwargs):
        super(PuzzleAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['reverse_unlocks'] = self.instance.puzzle_set.values_list('pk', flat=True)
            choices = self.instance.hunt.puzzle_set.values_list('pk', 'puzzle_name')
            self.fields['reverse_unlocks'].choices = choices

    def save(self, *args, **kwargs):
        instance = super(PuzzleAdminForm, self).save(*args, **kwargs)
        if instance.pk:
            instance.puzzle_set.clear()
            instance.puzzle_set.add(*self.cleaned_data['reverse_unlocks'])
        return instance

    class Meta:
        model = models.Puzzle
        fields = ('hunt', 'puzzle_name', 'puzzle_number', 'puzzle_id', 'answer', 'is_meta',
                  'doesnt_count', 'is_html_puzzle', 'link', 'resource_link', 'solution_link',
                  'extra_data', 'num_required_to_unlock', 'unlock_type', 'points_cost',
                  'points_value')


class PuzzleAdmin(admin.ModelAdmin):
    class Media:
        js = ("huntserver/admin_change_puzzle.js",)

    form = PuzzleAdminForm

    list_filter = ('hunt',)
    list_display = ['combined_id', 'puzzle_name', 'hunt', 'is_meta']
    list_display_links = ['combined_id', 'puzzle_name']
    ordering = ['-hunt', 'puzzle_number']
    inlines = (ResponseInline,)
    radio_fields = {"unlock_type": admin.VERTICAL}
    fieldsets = (
        (None, {
            'fields': ('hunt', 'puzzle_name', 'puzzle_number', 'puzzle_id', 'answer', 'is_meta',
                       'doesnt_count', 'is_html_puzzle', 'link', 'resource_link', 'solution_link',
                       'extra_data', 'unlock_type')
        }),
        ('Solve Unlocking', {
            'classes': ('formset_border', 'solve_unlocking'),
            'fields': ('reverse_unlocks', 'num_required_to_unlock')
        }),
        ('Points Unlocking', {
            'classes': ('formset_border', 'points_unlocking'),
            'fields': ('points_cost', 'points_value')
        }),
    )

    def combined_id(self, puzzle):
        return str(puzzle.puzzle_number) + "-" + puzzle.puzzle_id

    combined_id.short_description = "ID"


class ResponseAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'puzzle_just_name']
    ordering = ['-puzzle']

    def puzzle_just_name(self, response):
        return response.puzzle.puzzle_name

    puzzle_just_name.short_description = "Puzzle"


class SolveAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'solve_time']

    def solve_time(self, solve):
        return solve.submission.submission_time


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['submission_text', short_team_name, 'submission_time']


class TeamAdminForm(forms.ModelForm):
    persons = forms.ModelMultipleChoiceField(
        queryset=models.Person.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name=_('People'),
            is_stacked=False
        )
    )

    class Meta:
        model = models.Team
        fields = ['team_name', 'unlocked', 'hunt', 'location', 'join_code', 'playtester',
                  'num_available_hints', 'num_unlock_points', 'unlockables']

    def __init__(self, *args, **kwargs):
        super(TeamAdminForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['persons'].initial = self.instance.person_set.all()

    def save(self, commit=True):
        team = super(TeamAdminForm, self).save(commit=False)

        if commit:
            team.save()

        if team.pk:
            team.person_set.set(self.cleaned_data['persons'])
            self.save_m2m()

        return team


class TeamAdmin(admin.ModelAdmin):
    form = TeamAdminForm
    list_display = ['short_team_name', 'location', 'hunt', 'playtester']
    list_filter = ['hunt']

    def short_team_name(self, team):
        return truncatechars(team.team_name, 30) + " (" + str(team.size) + ")"

    short_team_name.short_description = "Team name"


class UnlockAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'time']


class UserProxyObject(User):
    class Meta:
        proxy = True
        app_label = 'huntserver'
        verbose_name = User._meta.verbose_name
        verbose_name_plural = User._meta.verbose_name_plural


class UserProxyAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name']
    search_fields = ['email', 'username', 'first_name', 'last_name']


admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.register(models.Hint,       HintAdmin)
admin.site.register(models.Hunt,       HuntAdmin)
admin.site.register(models.Message,    MessageAdmin)
admin.site.register(models.Person,     PersonAdmin)
admin.site.register(models.Prepuzzle,  PrepuzzleAdmin)
admin.site.register(models.Puzzle,     PuzzleAdmin)
admin.site.register(models.Response,   ResponseAdmin)
admin.site.register(models.Solve,      SolveAdmin)
admin.site.register(models.Submission, SubmissionAdmin)
admin.site.register(models.Team,       TeamAdmin)
admin.site.register(models.Unlockable)
admin.site.register(models.Unlock,     UnlockAdmin)
admin.site.register(UserProxyObject,   UserProxyAdmin)
