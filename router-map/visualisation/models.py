from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Visualisation(models.Model):
    name = models.CharField(max_length=127)
    display_link_descriptions = models.BooleanField(default=True)
    links_default_width = models.PositiveIntegerField(default=3,
                                                      validators=[MinValueValidator(1), MaxValueValidator(15)])
    highlighted_links_width = models.PositiveIntegerField(default=None, null=True, blank=True,
                                                          validators=[MinValueValidator(1), MaxValueValidator(15)])
    highlighted_links_range_min = models.PositiveIntegerField(default=None, null=True, blank=True,
                                                              help_text="links with higher or equal speed "
                                                                        "will be highlighted")
    highlighted_links_range_max = models.PositiveIntegerField(default=None, null=True, blank=True,
                                                              help_text="links with lower or equal speed "
                                                                        "will be highlighted")
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children',
                               on_delete=models.DO_NOTHING)

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


@receiver(post_delete, sender=Visualisation)
def location_post_delete_handler(sender, instance, **kwargs):
    Visualisation.objects.filter(parent=instance.id).update(parent=instance.parent)
