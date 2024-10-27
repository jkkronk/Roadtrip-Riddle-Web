import os
import requests
from geopy.geocoders import Nominatim
from geopy.distance import distance
import polyline
import mapillary as mly

def collect_images(time_in_seconds, city_name, data_folder, fps=24):
    """
    Collects images from Mapillary along routes leading to the specified city.
    The number of images collected will be sufficient to make a video of the specified time.
    The images are saved to the specified data folder.

    Parameters:
    - time_in_seconds (int): The length of the video to be made from the images.
    - city_name (str): The destination city.
    - data_folder (str): The folder where images will be saved.
    - fps (int, optional): Frames per second of the desired video. Default is 24.
    """

    # Ensure data_folder exists
    os.makedirs(data_folder, exist_ok=True)

    # Get coordinates of the city using geopy
    geolocator = Nominatim(user_agent="image_collector")
    location = geolocator.geocode(city_name)
    if location is None:
        print(f"Could not geocode city: {city_name}")
        return
    city_lat, city_lon = location.latitude, location.longitude

    # Define starting point 100 km away from the city at a bearing of 0 degrees
    origin = distance(kilometers=100).destination((city_lat, city_lon), bearing=0)
    origin_lat, origin_lon = origin.latitude, origin.longitude

    # Get route from origin to city using OSRM API
    route = get_route(origin_lat, origin_lon, city_lat, city_lon)
    if route is None:
        print("Could not get route between origin and city")
        return

    # Sample points along the route
    points = sample_route(route, time_in_seconds, fps)

    # For each point, get Mapillary images
    images_collected = 0
    mly.interface.set_access_token(os.getenv("MAPILLARY_API_TOKEN"))
    for idx, (lat, lon) in enumerate(points):
        image_url = get_mapillary_image(lat, lon)
        if image_url:
            # Download image
            image_path = os.path.join(data_folder, f"image_{idx}.jpg")
            download_image(image_url, image_path)
            images_collected += 1
        else:
            print(f"No image found at point ({lat}, {lon})")
    print(f"Collected {images_collected} images.")

def get_route(start_lat, start_lon, end_lat, end_lon):
    # Use OSRM API to get route between points
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=polyline"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['routes']:
            route_geometry = data['routes'][0]['geometry']
            route = polyline.decode(route_geometry)
            return route
    return None

def sample_route(route, time_in_seconds, fps):
    # Calculate the number of frames needed
    num_frames = time_in_seconds * fps
    route_length = len(route)
    if num_frames > route_length:
        # Loop over the route if necessary
        indices = [i % route_length for i in range(num_frames)]
    else:
        # Sample evenly along the route
        step = route_length / num_frames
        indices = [int(i * step) for i in range(num_frames)]
    sampled_points = [route[i] for i in indices]
    return sampled_points

def get_mapillary_image(lat, lon):
    """
    Fetches the URL of a Mapillary image close to the given latitude and longitude.

    Parameters:
    - lat (float): Latitude of the point.
    - lon (float): Longitude of the point.

    Returns:
    - image_url (str): URL of the image thumbnail, or None if no image is found.
    """

    # Fetch images close to the specified location using Mapillary SDK
    geojson = mly.interface.get_image_close_to(longitude=lon, latitude=lat, radius=100)

    if geojson and geojson.features:
        # Get the first image feature
        image_properties = geojson.features[0].properties
       
        image_url = mly.interface.image_thumbnail(image_properties.id, resolution=1024)
        return image_url
    else:
        return None

def download_image(url, path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, 'wb') as f:
            f.write(response.content)
