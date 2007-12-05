from cms import cms_global_settings
import re
from django.conf import settings
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext as _
from django import newforms as forms
from django.newforms.widgets import SelectMultiple
from cms import dynamicforms, util
from cms.cms_global_settings import *
from cms.models import Page, PageContent

slug_re = re.compile(r'^[-\w]+$')

DATETIME_FORMATS = (
    '%d.%m.%Y %H:%M:%S',     # '25.10.2006 14:30:59'
    '%d.%m.%Y %H:%M',        # '25.10.2006 14:30'
    '%d.%m.%Y',              # '25.10.2006'
    '%d.%m.%y %H:%M:%S',     # '25.10.06 14:30:59'
    '%d.%m.%y %H:%M',        # '25.10.06 14:30'
    '%d.%m.%y',              # '25.10.06'
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)
DATE_FORMATS = (
    '%d.%m.%Y',              # '25.10.2006'
    '%d.%m.%y',              # '25.10.06'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y',              # '10/25/06'
)

class DateTimeWidget(forms.widgets.SplitDateTimeWidget):
    def render(self, name, value, attrs=None):
        attrs.update({'class': 'vDateField'})
        return super(DateTimeWidget, self).render(name, value, attrs)

class DateWidget(forms.widgets.Input):
    input_type = 'text' # Subclasses must define this.

    def render(self, name, value, attrs=None):
        attrs.update({'class': 'vDateField'})
        return super(DateWidget, self).render(name, value, attrs)

class ModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    "A MultipleChoiceField with default help_text."
    def __init__(self, queryset, cache_choices=False, required=True,
            widget=SelectMultiple, label=None, initial=None, help_text=None):
        if not help_text:
            help_text = _(u'Hold down "Control", or "Command" on a Mac, to select more than one.')
        super(ModelMultipleChoiceField, self).__init__(queryset, cache_choices,
            required, widget, label, initial, help_text)

PAGE_FIELDS = (
    'title',
    'slug', 
    'template',
    'context',
    'is_published', 
    'in_navigation', 
    'override_url', 
    'overridden_url', 
    'start_publish_date', 
    'end_publish_date',
)
PAGECONTENT_FIELDS = (
    'language', 
    'is_published', 
    'content_type', 
    'title', 
    'content', 
    'description', 
    'allow_template_tags', 
    'template',
)

class PageForm(forms.Form):
    title = forms.CharField(max_length=200, help_text=_('The title of the page.'), label=_('title'))
    slug = forms.RegexField(slug_re, max_length=50, help_text=_('The name of the page that will appear in the URL. A slug can contain letters, numbers, underscores or hyphens.'), label=_('slug'))
    override_url = forms.BooleanField(label=_('override url'), help_text=_('When checked, a custom URL can be entered for this page.'), required=False)
    overridden_url = forms.CharField(label=_('overridden url'), help_text=_('Enter a url to use as custom url for this page.'), required=False)
    override_created = forms.DateTimeField(widget=DateWidget, required=False, input_formats=DATETIME_FORMATS, label=_('override created date'), help_text=_('Enter a date to use a custom creation date for this page.'))
    is_published = forms.BooleanField(required=False, initial=True, help_text=_('Whether or not the page will be accessible from the web.'), label=_('is published'))
    start_publish_date = forms.DateTimeField(widget=DateWidget, input_formats=DATE_FORMATS, required=False, label=_('start publishing'), help_text=_('Enter a date on which you want to start publishing this page.'))
    end_publish_date = forms.DateTimeField(widget=DateWidget, input_formats=DATE_FORMATS, required=False, label=_('finish publishing'), help_text=_('Enter a date after which you want to stop publishing this page.'))
    template = forms.ChoiceField(choices=cms_global_settings.TEMPLATES, help_text=_('The template that will be used to render the page. Choose nothing if you don\'t need a custom template.'), required=False)
    context  = forms.CharField(max_length=200, help_text=_('Optional. Dotted path to a python function that receives two arguments (request, context) and can update the context.'), required=False)
    parent = forms.ChoiceField(required=False, help_text=_('The page will be appended inside the chosen category.'), label=_('Navigation'))
    in_navigation = forms.BooleanField(required=False, label=_('display in navigation'), initial=True)
#    not yet implemented
#    change_access_level = ModelMultipleChoiceField(required=False, queryset=Group.objects.all(), label=_('change access level'), help_text=_('Select groups which are allowed to edit this page.'))
#    view_access_level = ModelMultipleChoiceField(required=False, queryset=Group.objects.all(), label=_('view access level'), help_text=_('If groups are selected, only these groups are allowed to view this page and every page rooted under it.'))

    def __init__(self, request, initial=None, page=None):
        self.page = page
        super(PageForm, self).__init__(request.method == 'POST' and request.POST or None, initial=initial)
        choices = [('', '--------')]
        choices += [(p.id, smart_unicode(p.get_path())) for p in util.flatten(Page.objects.hierarchy()) if p != page]
        self.fields['parent'].choices = choices
        choices = [('', '--------')]
        choices += cms_global_settings.TEMPLATES
        self.fields['template'].choices = choices

    def clean_parent(self):
        num_pages = Page.objects.count()
        if num_pages > 0: # If there are no pages, parent will be empty anyway
            if self.page and not self.page.parent and self.cleaned_data.get('parent'):
                raise forms.ValidationError(_('Please reorder the root object on the hierarchy page.'))
            if (not self.page or self.page.parent) and not self.cleaned_data.get('parent'):
                raise forms.ValidationError(_('Please choose in which category the page should belong.'))
        return self.cleaned_data.get('parent')

class PageContentForm(dynamicforms.Form):
    PREFIX = 'pagecontent'
    TEMPLATE = 'cms/pagecontent_form.html'
    CORE = (
        'content', 
        'description', 
        'title',
    )
    CONTENT_TYPES = (
        ('html', _('HTML')), 
        ('markdown', _('Markdown')), 
        ('text', _('Plain text')),
    )

    language = forms.ChoiceField(choices=((lang_code, _(lang)) for lang_code, lang in settings.LANGUAGES), initial=settings.LANGUAGE_CODE[:2], label=_('language'))
    is_published = forms.BooleanField(required=False, initial=True, label=_('is published'))
    title = forms.CharField(max_length=200, required=False, help_text=_('Leave this empty to use the title of the page.'), label=_('title'))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 10, 'cols': 80}), label=_('description'))
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 20, 'cols': 80}), label=_('content'))
    content_type = forms.ChoiceField(choices=CONTENT_TYPES, initial=USE_TINYMCE and 'html' or 'markdown', label=_('content type'))
    allow_template_tags = forms.BooleanField(required=False, initial=True, label=_('allow template tags'))
    template = forms.CharField(max_length=200, required=False, label=_('template (optional)'))

    def __unicode__(self):
        return self.id and smart_unicode(PageContent.objects.get(pk=self.id)) or _('New page content')

    def from_template(self, extra_context={}):
        extra_context.update({'use_description': PAGECONTENT_DESCRIPTION})
        return super(PageContentForm, self).from_template(extra_context)