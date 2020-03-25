import csv
from io import StringIO

from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.utils import DataError
from django.shortcuts import render
