from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse


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
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.DO_NOTHING,
                               help_text="parent node in tree view of visualisations")

    def clean(self):
        error_dict = {}
        if self.parent:
            if self.parent.id == self.id:
                error_dict['parent'] = ValidationError('This field value cannot point to itself.')
            elif self.parent.is_ancestor(self):
                error_dict['parent'] = ValidationError('The descendant can not be a parent.')
        if self.highlighted_links_width and self.highlighted_links_range_min and self.highlighted_links_range_max:
            if self.highlighted_links_range_max < self.highlighted_links_range_min:
                error_dict['highlighted_links_range_max'] = ValidationError(
                    'Ensure this value is greater than or equal to highlighted links range min.')
        elif self.highlighted_links_width or self.highlighted_links_range_min or self.highlighted_links_range_max:
            if not self.highlighted_links_width:
                error_dict['highlighted_links_width'] = ValidationError('This field is required.')
            if not self.highlighted_links_range_min:
                error_dict['highlighted_links_range_min'] = ValidationError('This field is required.')
            if not self.highlighted_links_range_max:
                error_dict['highlighted_links_range_max'] = ValidationError('This field is required.')
        if error_dict:
            raise ValidationError(error_dict)

    def is_ancestor(self, visualisation):
        if not self.parent:
            return False
        elif self.parent.id == visualisation.id:
            return True
        else:
            return self.parent.is_ancestor(visualisation)

    def get_absolute_url(self):
        if hasattr(self, 'map'):
            return reverse('map:index', kwargs={'map_pk': self.pk})
        elif hasattr(self, 'diagram'):
            return reverse('diagram:index', kwargs={'diagram_pk': self.pk})

    def __str__(self):
        return self.name


@receiver(post_delete, sender=Visualisation)
def location_post_delete_handler(sender, instance, **kwargs):
    Visualisation.objects.filter(parent=instance.id).update(parent=instance.parent)
