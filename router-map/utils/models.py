from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class Visualisation(models.Model):
    name = models.TextField()
    display_link_descriptions = models.BooleanField(default=True)
    links_default_width = models.PositiveIntegerField(default=3,
                                                      validators=[MinValueValidator(1), MaxValueValidator(15)])
    highlighted_links_width = models.PositiveIntegerField(default=None, null=True, blank=True,
                                                          validators=[MinValueValidator(1), MaxValueValidator(15)])
    highlighted_links_range_min = models.PositiveIntegerField(default=None, null=True, blank=True)
    highlighted_links_range_max = models.PositiveIntegerField(default=None, null=True, blank=True)

    def clean(self):
        if self.highlighted_links_width and self.highlighted_links_range_min and self.highlighted_links_range_max:
            if self.highlighted_links_range_max < self.highlighted_links_range_min:
                raise ValidationError({'highlighted_links_range_max': ValidationError(
                    'Ensure this value is greater than or equal to highlighted links range min.')})

        elif self.highlighted_links_width or self.highlighted_links_range_min or self.highlighted_links_range_max:
            error_dict = {}
            if not self.highlighted_links_width:
                error_dict['highlighted_links_width'] = ValidationError('This field is required.')
            if not self.highlighted_links_range_min:
                error_dict['highlighted_links_range_min'] = ValidationError('This field is required.')
            if not self.highlighted_links_range_max:
                error_dict['highlighted_links_range_max'] = ValidationError('This field is required.')
            raise ValidationError(error_dict)

    class Meta:
        abstract = True
