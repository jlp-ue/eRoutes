from django.shortcuts import render
from datetime import timedelta
import pandas as pd

from .api_handler import *
from .ajax_handler import *
from .charging_stations import *
from .charging_station_prices import *
from .direction_data import *
from .battery_data import *



def index2(request):
    # Get list of all cars from csv
    cars_frame = pd.read_csv("C:/Users/David/Desktop/eCars.csv", sep=';')
    cars_list = cars_frame["Car"].tolist()
    return render(request, 'routing/index.html', {"cars_list": cars_list})

def index(request):
    connection = mysql.connector.connect(user='dsteiner', password='eMobility2018DS',
                                             host='mobility.f4.htw-berlin.de',
                                             database='electric_vehicles', buffered=True)

    # get list of all cars from database
    try:
        cursor = connection.cursor()
        selectString = ("select name from vehicles")
        cursor.execute(selectString)
        cars_list = []

        for name in cursor:
            cars_list.append(name[0])

        #cars_list = cars_list[1:]
        return render(request, 'routing/index.html', {"cars_list": cars_list})

    finally:
        connection.commit()
        connection.close()


def team(request):
    return render(request, 'routing/team.html')


def error(request):
    return render(request, 'routing/error.html')


def contact(request):
    return render(request, 'routing/contact.html')


def algorithm(request):
    return render(request, 'routing/algorithm.html')


def search(request):
    if 'start' in request.POST:
        message = 'You searched for: %r' % request.POST['start']
    else:
        message = 'You submitted an empty form.'
    return render(request, message)


def output(request):
    if request.method == 'POST':
        start = request.POST.get('start', 'leer')
        destination = request.POST.get('destination', 'leer')
        car = request.POST.get('car', 'leer')
        driving_style = request.POST.get('driving_style', 'leer')
        battery_status = request.POST.get('battery_status', 'leer')


        # get all direction and car data from database:
        route_json = get_direction_data(start, destination, car, battery_status, driving_style)

        # Price and Provider Data // MISSING charging speed, capacity etc
        price_provider_data = route_json['charging_station_data']




        # Waypoints string
        waypoints = route_json['waypoints_return']

        # Routing URL
        url = route_json['google_url']
        car_range = round(route_json['range_of_car'], 0) / 1000

        # Total Distance of trip
        distance_array = []
        for i in range(len(route_json['routes'][0]['legs'])):
            charging_station = route_json['routes'][0]['legs'][i]['distance']['value']
            distance_array.append(charging_station)
        distance = sum(distance_array)

        # Driving Time
        driving_time_array = []
        for i in range(len(route_json['routes'][0]['legs'])):
            charging_station = route_json['routes'][0]['legs'][i]['duration']['value']
            driving_time_array.append(charging_station)
        driving_time_min = round(sum(driving_time_array) / 60, 0)

        # build output-string of data from charging stations along the way
        charging_station = route_json['routes'][0]['legs']
        battery_capacity = getBatteryData(car, "battery_capacity_kwh")
        fastcharging_time = getBatteryData(car, "fastcharge_time")

        all_waypoints_string = []
        charging_price_list = []
        charging_time_list = []

        for i in range(len(charging_station)-1):
            address2 = charging_station[i]['end_address']
            distance2 = charging_station[i]['distance']['text']
            duration2 = charging_station[i]['duration']['text']
            #charge_list = price_provider_data[i]
            provider = price_provider_data[i][0]
            price_cent = price_provider_data[i][1]

            #level of battery
            battery_level = distance_array[i] / car_range



            #Charging Price (Battery Capacity * battery_level * price_cent
            charging_price = round((battery_capacity * price_cent) / 1000,2)
            charging_price_list.append(charging_price)

            #charging_time (Charging time * battery_level)
            charging_time = int(round((int(fastcharging_time) * int(battery_level)) / 1000 ,0))
            charging_time_list.append(charging_time)

            text = provider + '\n' + str(price_cent) + ' Euro/kWh' + '\n' + address2 + '\n' + distance2 + '\n' + duration2  + '\n' + "Charging Price: " + str(
                charging_price) + " Euro" + '\n' + "Charging Time: " + str(charging_time) + " min"

            all_waypoints_string.append(text)

        # total time, waiting time, charging time
        count_stations = len(charging_station)-1
        charging_time_min = 30 * count_stations
        #charging_time_min = sum(charging_time)
        waiting_time_min = 2 * count_stations
        total_time = min_to_hour(driving_time_min + charging_time_min + waiting_time_min)
        driving_time = min_to_hour(driving_time_min)
        charging_time = min_to_hour(charging_time_min)
        waiting_time = min_to_hour(waiting_time_min)

        # Weather and geo api call
        temperature_start = get_weather_start(start)
        temperature_destination = get_weather_destination(destination)
        #geo_coordinates = get_geo_data(start)

        # Calculate Overview Data (total cost, money saved, distance)
        #total_cost = sum(charging_price_list)
        total_cost = round((distance / 1000) * 1.6 * 0.025, 2)
        money_saved = round(((distance / 1000) * 1.6 * 0.13) - total_cost, 2)
        distance = round(distance / 1000, 1)

        return render(request, 'routing/output.html', {'start': start,
                                                       'destination': destination,
                                                       'car': car,
                                                       'driving_style': driving_style,
                                                       'battery_status': battery_status,
                                                       'temperature_start': temperature_start,
                                                       'temperature_destination': temperature_destination,
                                                       'distance': distance,
                                                       'total_cost': total_cost,
                                                       'money_saved': money_saved,
                                                       'waypoints': waypoints,
                                                       'driving_time': driving_time,
                                                       'all_waypoints_string': all_waypoints_string,
                                                       'charging_time': charging_time,
                                                       'waiting_time': waiting_time,
                                                       'total_time': total_time,
                                                       'url': url,
                                                       'car_range': car_range,
                                                       })
    else:
        return render(request, 'routing/output.html')


def min_to_hour(min):
    return str(timedelta(minutes=min))[:-3]
