from django.shortcuts import render
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from fire.models import Incident, Locations, WeatherConditions, FireStation, FireTruck ,Firefighters
from fire.forms import FireStationzForm, Incident_Form, Loc_Form, Weather_condition, Firetruckform, FirefightersForm
from django.db import connection
from django.http import JsonResponse
from django.db.models.functions import ExtractMonth

from django.db.models import Count
from datetime import datetime

from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from django.contrib import messages


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


# FireStation CRUD Views


def firestation_list(request):
    firestations = FireStation.objects.all()
    return render(request, 'station_list.html', {'object_list': firestations})


class firestationListView(ListView):
    model = FireStation
    template_name = 'station_list.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query) |
                Q(country__icontains=query)
            )
        return qs


class firestationCreateView(CreateView):
    model = FireStation
    form_class = FireStationzForm
    template_name = 'station_add.html'
    success_url = reverse_lazy('station-list')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        messages.success(
            self.request, f" '{name} Fire Station added successfully.'")
        return super().form_valid(form)


class firestationUpdateView(UpdateView):
    model = FireStation
    form_class = FireStationzForm
    template_name = 'station_update.html'
    success_url = reverse_lazy('station-list')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        messages.success(
            self.request, f"'{name}' Fire Station updated successfully.")
        return super().form_valid(form)


class firestationDeleteView(DeleteView):
    model = FireStation
    template_name = 'station_delete.html'
    success_url = reverse_lazy('station-list')

    def form_valid(self, form):
        name = self.object.name
        messages.success(
            self.request, f"'{name}' Fire Station deleted successfully.")
        return super().form_valid(self)

# Incident CRUD Views


class IncidentListView(ListView):
    model = Incident
    template_name = 'incident_list.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(description__icontains=query) |
                Q(severity_level__icontains=query) |
                # Assuming Locations model has a 'name' field
                Q(location__name__icontains=query) |
                # Assuming you want to search by date_time
                Q(date_time__icontains=query)
            )
        return qs


class IncidentCreateView(CreateView):
    model = Incident
    form_class = Incident_Form
    template_name = 'incident_add.html'
    success_url = reverse_lazy('incident-list')

    def form_valid(self, form):
        location = form.cleaned_data['location']
        messages.success(
            self.request, f" '{location} Incident added successfully.'")
        return super().form_valid(form)


class IncidentUpdateView(UpdateView):
    model = Incident
    form_class = Incident_Form
    template_name = 'incident_update.html'
    success_url = reverse_lazy('incident-list')

    def form_valid(self, form):
        location = form.cleaned_data['location']
        messages.success(
            self.request, f" '{location} Incident updated successfully.'")
        return super().form_valid(form)


class IncidentDeleteView(DeleteView):
    model = Incident
    template_name = 'incident_delete.html'
    success_url = reverse_lazy('incident-list')

    def form_valid(self, form):
        location = self.object.location
        messages.success(
            self.request, f" {location} Incident deleted successfully.")
        return super().form_valid(form)


# Location CRUD

class LocationListView(ListView):
    model = Locations
    template_name = 'location_list.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query) |
                Q(country__icontains=query)
            )
        return qs


class LocationCreateView(CreateView):
    model = Locations
    form_class = Loc_Form
    template_name = 'location_add.html'
    success_url = reverse_lazy('loc-list')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        messages.success(
            self.request, f" '{name} location added successfully.'")
        return super().form_valid(form)


class LocationUpdateView(UpdateView):
    model = Locations
    form_class = Loc_Form
    template_name = 'location_update.html'
    success_url = reverse_lazy('loc-list')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        messages.success(
            self.request, f" '{name} location updated successfully.'")
        return super().form_valid(form)


class LocationDeleteView(DeleteView):
    model = Locations
    template_name = 'location_delete.html'
    success_url = reverse_lazy('loc-list')

    def form_valid(self, form):
        name = self.object.name
        messages.success(
            self.request, f" {name} Firestation deleted successfully.")
        return super().form_valid(form)


# Weather CRUD


class ConditionListView(ListView):
    model = WeatherConditions
    context_object_name = 'object_list'
    template_name = 'weather_list.html'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super(ConditionListView, self).get_queryset(*args, **kwargs)
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(incident__location__name__icontains=query) |
                Q(temperature__icontains=query) |
                Q(humidity__icontains=query) |
                Q(wind_speed__icontains=query) |
                Q(weather_description__icontains=query)
            )
        return qs


class ConditionCreateView(CreateView):
    model = WeatherConditions
    form_class = Weather_condition
    template_name = 'weather_add.html'
    success_url = reverse_lazy('weather-list')

    def form_valid(self, form):
        incident = form.cleaned_data['incident']
        messages.success(
            self.request, f" '{incident} location updated successfully.'")
        return super().form_valid(form)


class ConditionUpdateView(UpdateView):
    model = WeatherConditions
    form_class = Weather_condition
    template_name = 'weather_update.html'
    success_url = reverse_lazy('weather-list')

    def form_valid(self, form):
        incident = form.cleaned_data['incident']
        messages.success(
            self.request, f" '{incident} location updated successfully.'")
        return super().form_valid(form)


class ConditionDeleteView(DeleteView):
    model = WeatherConditions
    template_name = 'weather_delete.html'
    success_url = reverse_lazy('weather-list')

    def form_valid(self, form):
        incident = self.object.incident
        messages.success(
            self.request, f" {incident} condition deleted successfully.")
        return super().form_valid(form)

# FireTruck CRUD


class FiretruckListView(ListView):
    model = FireTruck
    context_object_name = 'firetruck'
    template_name = 'firetruck_list.html'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(truck_number__icontains=query) |
                Q(model__icontains=query) |
                Q(capacity__icontains=query) |
                Q(station__name__icontains=query))

        return qs


class FiretruckCreateView(CreateView):
    model = FireTruck
    form_class = Firetruckform
    template_name = 'firetruck_add.html'
    success_url = reverse_lazy('fireTruck-list')

    def form_valid(self, form):
        truck_number = form.cleaned_data['truck_number']
        messages.success(
            self.request, f" '{truck_number} fire truck added successfully.'")
        return super().form_valid(form)


class FiretruckUpdateView(UpdateView):
    model = FireTruck
    form_class = Firetruckform
    template_name = 'firetruck_update.html'
    success_url = reverse_lazy('fireTruck-list')

    def form_valid(self, form):
        truck_number = form.cleaned_data['truck_number']
        messages.success(
            self.request, f" '{truck_number} fire truck updated successfully.'")
        return super().form_valid(form)


class FiretruckDeleteView(DeleteView):
    model = FireTruck
    template_name = 'firetruck_delete.html'
    success_url = reverse_lazy('fireTruck-list')

    def form_valid(self, form):
        truck_number = self.object.truck_number
        messages.success(
            self.request, f" {truck_number} fire truck deleted successfully.")
        return super().form_valid(form)


# FireFighter CRUD


class FirefightersListView(ListView):
    model = Firefighters
    context_object_name = 'firefighters'
    template_name = 'firefighter_list.html'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(name__icontains=query))
        return qs


class FirefightersCreateView(CreateView):
    model = Firefighters
    form_class = FirefightersForm
    template_name = 'firefighter_add.html'
    success_url = reverse_lazy('firefighters-list')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        messages.success(
            self.request, f" '{name} Fire fighter added successfully.'")
        return super().form_valid(form)


class FirefightersUpdateView(UpdateView):
    model = Firefighters
    form_class = FirefightersForm
    template_name = 'firefighter_update.html'
    success_url = reverse_lazy('firefighters-list')

    def form_valid(self, form):
        name = form.cleaned_data['name']
        messages.success(
            self.request, f" '{name} Fire fighter updated successfully.'")
        return super().form_valid(form)


class FirefightersDeleteView(DeleteView):
    model = Firefighters
    template_name = 'firefighter_delete.html'
    success_url = reverse_lazy('firefighters-list')

    def form_valid(self, form):
        name = self.object.name
        messages.success(
            self.request, f" {name} Fire fighter deleted successfully.")
        return super().form_valid(form)
