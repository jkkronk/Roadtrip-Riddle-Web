import os
import requests
from geopy.geocoders import Nominatim
from geopy.distance import distance
import polyline
import mapillary as mly
import math
import random
import concurrent.futures
from itertools import islice

def collect_images(city_name, data_folder, distance_to_city=100, num_images=3000):
    """
    Collects images from Mapillary along routes leading to the specified city.
    The number of images collected will be sufficient to make a video of the specified time.
    The images are saved to the specified data folder.

    Parameters:
    - city_name (str): The destination city.
    - data_folder (str): The folder where images will be saved.
    - distance_to_city (int): The distance in kilometers from the city to the starting point.
    - num_images (int): The number of images to collect.
    """

    # Ensure data_folder exists
    street_view_folder = os.path.join(data_folder, 'street_view_frames')
    os.makedirs(data_folder, exist_ok=True)
    os.makedirs(street_view_folder, exist_ok=True)

    # Get coordinates of the city using geopy
    geolocator = Nominatim(user_agent="image_collector")
    location = geolocator.geocode(city_name)
    if location is None:
        print(f"Could not geocode city: {city_name}")
        return
    city_lat, city_lon = location.latitude, location.longitude

    # Define starting point distance km away from the city at a random bearing
    bearing = random.randint(0, 360)
    origin = distance(kilometers=distance_to_city).destination((city_lat, city_lon), bearing=bearing)
    origin_lat, origin_lon = origin.latitude, origin.longitude

    # Get route from origin to city using OSRM API
    route = get_route(origin_lat, origin_lon, city_lat, city_lon)
    if route is None:
        print("Could not get route between origin and city")
        return

    # Sample points along the route and compute bearings
    print(f"Sampling {num_images} points")
    print(f"Route length: {len(route)}")
    points, bearings = sample_route(route, num_images)
    print(f"Sampled {len(points)} points")

    # Remove the first and last 500 elements
    points = points[500:-500]
    bearings = bearings[500:-500]

    print(f"Processing {len(points)} points")
    # Process points in batches for parallel processing
    BATCH_SIZE = 50
    images_collected = 0
    prev_seq_id = None
    prev_id = None
    mly.interface.set_access_token(os.getenv("MAPILLARY_API_TOKEN"))
    collected_image_coords = []
    
    for i in range(0, len(points), BATCH_SIZE):
        batch_points = points[i:i + BATCH_SIZE]
        batch_bearings = bearings[i:i + BATCH_SIZE]
        
        # Parallelize image URL collection
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures_map = {}
            for j, ((lat, lon), bearing) in enumerate(zip(batch_points, batch_bearings)):
                abs_index = i + j  # absolute index in the entire points list
                future = executor.submit(get_mapillary_image, lat, lon, bearing, prev_seq_id)
                futures_map[future] = (abs_index, lat, lon, bearing)

            image_data = []
            for future in concurrent.futures.as_completed(futures_map):
                try:
                    abs_index, lat, lon, bearing = futures_map[future]
                    image_url, seq_id, img_id = future.result()
                    if image_url and img_id != prev_id:
                        image_data.append((image_url, img_id, lat, lon, bearing, abs_index))
                        prev_seq_id = seq_id
                        prev_id = img_id
                        images_collected += 1
                except Exception as e:
                    print(f"Failed to process image: {str(e)}")
                    continue
                print(f"Processed point {abs_index + 1} of {len(points)}")
        
        # Sort image_data by the absolute index before downloading
        image_data.sort(key=lambda x: x[5])
        
        # Download images in parallel, maintaining the correct order
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            download_futures = []
            # The start index for saved images depends on how many have been collected so far
            # Note: images_collected already incremented for each added image above
            start_index = images_collected - len(image_data)
            for idx, (url, _, lat, lon, bearing, _) in enumerate(image_data, start=start_index):
                image_path = os.path.join(street_view_folder, f"image_{idx}.jpg")
                download_futures.append(executor.submit(download_image, url, image_path))
            
            concurrent.futures.wait(download_futures)
            
            # Add successful downloads to collected coords
            for url, _, lat, lon, bearing, _ in image_data:
                collected_image_coords.append((lat, lon, bearing))

    return collected_image_coords

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

def compute_bearing(lat1, lon1, lat2, lon2):
    """
    Computes the bearing between two points.

    Parameters:
    - lat1, lon1: Latitude and longitude of the first point.
    - lat2, lon2: Latitude and longitude of the second point.

    Returns:
    - bearing (float): Bearing in degrees from north.
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    diff_long = math.radians(lon2 - lon1)

    x = math.sin(diff_long) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        (math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_long))

    initial_bearing = math.atan2(x, y)
    # Convert from radians to degrees and normalize
    bearing = (math.degrees(initial_bearing) + 360) % 360
    return bearing

def sample_route(route, num_images):
    """
    Samples points along the route and computes their bearings.

    Returns:
    - sampled_points (list of tuples): List of (lat, lon) tuples.
    - bearings (list of floats): List of bearings corresponding to each point.
    """
    route_length = len(route)
    if num_images > route_length:
        raise ValueError("Number of images is greater than the length of the route")
    
    # Sample evenly along the route
    step = int(route_length / num_images)
    indices = [int(i * step) for i in range(num_images)]
    sampled_points = [route[i] for i in indices]

    # Compute bearings between consecutive points
    bearings = []
    for i in range(len(sampled_points) - 1):
        lat1, lon1 = sampled_points[i]
        lat2, lon2 = sampled_points[i + 1]
        bearing = compute_bearing(lat1, lon1, lat2, lon2)
        bearings.append(bearing)
    # Repeat the last bearing for the final point
    bearings.append(bearings[-1])

    return sampled_points, bearings

def get_mapillary_image(lat, lon, desired_bearing, prev_seq_id=None):
    radius = 100 
    angle_tolerance = 45
    
    geojson = mly.interface.get_image_looking_at(
        at={"lng": lon, "lat": lat}, 
        radius=radius,
        image_type="flat",
    )
    
    if not geojson or not geojson.features:
        return None, None, None
        
    # Find the best matching image based on bearing
    best_image = None
    best_angle_diff = angle_tolerance
    
    for feature in geojson.features:
        image_properties = feature.properties
        image_bearing = image_properties.compass_angle
        
        angle_diff = min(
            abs(image_bearing - desired_bearing),
            360 - abs(image_bearing - desired_bearing)
        )
        
        if image_properties.sequence_id == prev_seq_id:
            best_image = image_properties
            break

        if angle_diff <= best_angle_diff:
            best_angle_diff = angle_diff
            best_image = image_properties
    
    if best_image:
        image_url = mly.interface.image_thumbnail(best_image.id, resolution=1024)
        return image_url, best_image.sequence_id, best_image.id
    
    return None, None, None

def download_image(url, path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, 'wb') as f:
            f.write(response.content)
