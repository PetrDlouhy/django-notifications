import warnings

from django.template import Context, Template
from django.test import SimpleTestCase

try:
    from django.utils.deprecation import RemovedInDjango60Warning
except ImportError:  # pragma: no cover
    RemovedInDjango60Warning = DeprecationWarning


class TemplateTagDeprecationTests(SimpleTestCase):
    def _render_without_django60_warning(self, template):
        with warnings.catch_warnings():
            warnings.simplefilter('error', RemovedInDjango60Warning)
            rendered = Template('{% load notifications_tags %}' + template).render(Context({}))
        return rendered

    def test_register_notify_callbacks_does_not_emit_removed_in_django60_warning(self):
        rendered = self._render_without_django60_warning('{% register_notify_callbacks %}')
        self.assertIn('<script type="text/javascript">', rendered)
        self.assertIn('register_notifier();', rendered)

    def test_live_notify_list_does_not_emit_removed_in_django60_warning(self):
        rendered = self._render_without_django60_warning('{% live_notify_list %}')
        self.assertEqual(rendered, "<ul class='live_notify_list'></ul>")
