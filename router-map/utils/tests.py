from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Visualisation


class TestMapForm(TestCase):
    def test_visualisation_model(self):
        visual = Visualisation()
        self.assertRaises(ValidationError, visual.full_clean)

    def test_visualisation_model_name(self):
        visual = Visualisation(name='a')
        self.assertTrue(visual.full_clean)

    def test_visualisation_model_highlighted_links_width_no_exist(self):
        visual = Visualisation(name='a', highlighted_links_range_min=3, highlighted_links_range_max=5)
        self.assertRaises(ValidationError, visual.full_clean)

    def test_visualisation_model_highlighted_links_range_max_lower_than_min(self):
        visual = Visualisation(name='a', highlighted_links_width=8, highlighted_links_range_min=3,
                               highlighted_links_range_max=2)
        self.assertRaises(ValidationError, visual.full_clean)
