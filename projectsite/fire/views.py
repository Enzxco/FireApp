from django.shortcuts import render
from django.views.generic.list import ListView
from fire.models import Locations, Incident, FireStation
from django.db import connection
from django.http import JsonResponse
from django.db.models.functions import ExtractMonth

from django.db.models import Count
from datetime import datetime


class HomePageView(ListView):
    model = Locations
    context_object_name = 'home'
    template_name = "home.html"


class ChartView(ListView):
    template_name = 'chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_queryset(self, *args, **kwargs):
        pass


def PieCountbySeverity(request):
    print("test")
    query = '''
        SELECT severity_level, COUNT(*) as count
        FROM fire_incident
        GROUP BY severity_level
    '''
    data = {}

    
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    if rows:
        # Construct the dictionary with severity level as keys and count as
        # values
        data = {severity: count for severity, count in rows}
    else:
        data = {}
    print(data)
    return JsonResponse(data)


def map_station(request):
    fireStations = FireStation.objects.values('name', 'latitude', 'longitude')

    for fs in fireStations:
        fs['latitude'] = float(fs['latitude'])
        fs['longitude'] = float(fs['longitude'])

    fireStations_list = list(fireStations)

    context = {
        'fireStations': fireStations_list,
    }

    return render(request, 'map_station.html', context)


def map_incident(request):
    fireIncident = Locations.objects.values('name', 'latitude', 'longitude')

    for fs in fireIncident:
        fs['latitude'] = float(fs['latitude'])
        fs['longitude'] = float(fs['longitude'])

    fireIncident_list = list(fireIncident)

    context = {
        'fireIncident': fireIncident_list,
    }

    return render(request, 'map_incident.html', context)


def LineCountbyMonth(request):
    current_year = datetime.now().year
    
    # Initialize result dictionary with zeros for all months
    result = {month: 0 for month in range(1, 13)}
    
    # Get incidents for current year and count by month
    incidents_per_month = Incident.objects.filter(date_time__year=current_year) \
        .annotate(month=ExtractMonth('date_time')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')
    
    # Update result with actual counts
    for item in incidents_per_month:
        month = item['month']
        result[month] = item['count']
    
    # Month names mapping
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    
    # Convert month numbers to names
    result_with_month_names = {
        month_names[month]: count for month, count in result.items()
    }
    
    return JsonResponse(result_with_month_names)


def MultilineIncidentTop3Country(request):
    current_year = datetime.now().year
    
    # Get top 3 countries by incident count
    top_countries = Incident.objects.select_related('location') \
        .values('location__country') \
        .annotate(total=Count('id')) \
        .order_by('-total')[:3] \
        .values_list('location__country', flat=True)
    
    # Initialize result dictionary
    result = {}
    
    # For each top country, get monthly incident counts
    for country in top_countries:
        monthly_data = Incident.objects.filter(
            location__country=country,
            date_time__year=current_year
        ).annotate(
            month=ExtractMonth('date_time')
        ).values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')
        
        # Initialize country data with zeros for all months
        result[country] = {month: 0 for month in range(1, 13)}
        
        # Update with actual counts
        for item in monthly_data:
            result[country][item['month']] = item['count']
    
    # Ensure all months are present and ordered
    for country in result:
        result[country] = {str(month).zfill(2): result[country][month] 
                         for month in range(1, 13)}
    
    return JsonResponse(result)


def multipleBarbySeverity(request):
    current_year = datetime.now().year
    
    # Get all severity levels
    severity_levels = Incident.objects.values_list('severity_level', flat=True).distinct()
    
    # Initialize result dictionary
    result = {level: {str(month).zfill(2): 0 for month in range(1, 13)} 
             for level in severity_levels}
    
    # Get monthly counts for each severity level
    monthly_data = Incident.objects.filter(date_time__year=current_year) \
        .annotate(month=ExtractMonth('date_time')) \
        .values('severity_level', 'month') \
        .annotate(count=Count('id')) \
        .order_by('severity_level', 'month')
    
    # Update result with actual counts
    for item in monthly_data:
        severity = item['severity_level']
        month = str(item['month']).zfill(2)
        result[severity][month] = item['count']
    
    return JsonResponse(result)