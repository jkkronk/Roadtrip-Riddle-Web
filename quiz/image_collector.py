import os
import requests
from geopy.geocoders import Nominatim
from geopy.distance import distance
import polyline
import mapillary as mly
import math
import random
from collections import defaultdict

class ImageCollector:    
    def __init__(self, city_name, output_folder, distance_to_city=100):
        self.city_name = city_name
        self.output_folder = output_folder
        self.distance_to_city = distance_to_city
        
        # Internal attributes
        self.street_view_folder = os.path.join(self.output_folder, 'street_view_frames')
        self._ensure_directories()
        
        # Geopy setup for city coordinates
        self.geolocator = Nominatim(user_agent="image_collector")

        # Mapillary authentication
        mly.interface.set_access_token(os.getenv("MAPILLARY_API_TOKEN"))

    def collect_images(self):
        """
        The main method to collect images from Mapillary. It:
        - Geocodes the city to get its coordinates.
        - Determines a starting point some distance away from the city.
        - Fetches a route from the starting point to the city.
        - Samples points along the route and finds appropriate images from Mapillary.
        - Downloads the images to the specified folder.

        Returns:
        - A list of tuples (lat, lon, bearing) for each collected image.
        """
        # Get city and start coordinates
        city_lat, city_lon = self._geocode_city()
        origin_lat, origin_lon = self._get_origin_point(city_lat, city_lon)

        # Get route geometry
        route = self._get_route(origin_lat, origin_lon, city_lat, city_lon)
        bearings = self._calculate_bearings(route)
        # only keep the last 4 points
        route = route[-800:]
        bearings = bearings[-800:]

        # Get the image features from Mapillary
        image_features, sequence_ids = self._get_image_features(route, bearings)
        print(f"Found {len(image_features)} image features")
        print(f"Sequence IDs: {sequence_ids}")
        print(f"found images in first element {image_features[0]}")
        # For each element in image features, only keep the image with the highest amount of 
        # images in the entire route. 
        cleaned_image_features = self._clean_image_features(image_features, sequence_ids)
        print(f"Found {len(cleaned_image_features)} cleaned image features")
        print(f"found images in first element {cleaned_image_features[0]}")
        print(f"found images in last element {cleaned_image_features[-1]}")
        # Download the images to the specified folder. 
        self._download_images(cleaned_image_features)

        return route, bearings

    def _ensure_directories(self):
        """
        Ensure the data and street view frames directories exist.
        """
        os.makedirs(self.street_view_folder, exist_ok=True)
    
    def _geocode_city(self):
        """
        Geocode the city to obtain its latitude and longitude.

        Returns:
        - city_lat, city_lon: Coordinates of the city or (None, None) if not found.
        """
        location = self.geolocator.geocode(self.city_name)
        if location is None:
            return None, None
        city_lat, city_lon = location.latitude, location.longitude
        if city_lat is None or city_lon is None:
            print(f"Could not geocode city: {self.city_name}")
            return []
        return city_lat, city_lon

    def _get_origin_point(self, city_lat, city_lon):
        """
        Determine the origin point at a random bearing away from the city.

        Parameters:
        - city_lat, city_lon: Coordinates of the city.

        Returns:
        - origin_lat, origin_lon: Coordinates of the origin point.
        """
        bearing = random.randint(0, 360)
        origin = distance(kilometers=self.distance_to_city).destination((city_lat, city_lon), bearing=bearing)
        return origin.latitude, origin.longitude

    def _get_route(self, start_lat, start_lon, end_lat, end_lon):
        """
        Fetch a route from an OSRM API between the start and end points.
        
        Parameters:
        - start_lat, start_lon: Coordinates of the start point.
        - end_lat, end_lon: Coordinates of the end point (destination).

        Returns:
        - route: A list of (lat, lon) pairs representing the route.
                 None if the route couldn't be fetched.
        """
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=polyline"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                route_geometry = data['routes'][0]['geometry']
                route = polyline.decode(route_geometry)
                return route
        return None

    def _calculate_bearings(self, route):
        """Compute bearings between consecutive sampled points"""
        
        bearings = []
        for i in range(len(route) - 1):
            lat1, lon1 = route[i]
            lat2, lon2 = route[i + 1]
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            diff_long = math.radians(lon2 - lon1)

            x = math.sin(diff_long) * math.cos(lat2_rad)
            y = (math.cos(lat1_rad) * math.sin(lat2_rad) 
                 - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_long))

            initial_bearing = math.atan2(x, y)
            bearings.append((math.degrees(initial_bearing) + 360) % 360)

        # Repeat last bearing for the final point
        bearings.append(bearings[-1])
        return bearings
    

    def _download_images(self, image_features):
        """
        Download the images to the specified folder. 
        """
        for idx, image_feature in enumerate(image_features):
            url = mly.interface.image_thumbnail(image_feature['id'])
            path = os.path.join(self.street_view_folder, f"{idx}.jpg")
            print(f"Downloading image from {url} to {path}")
            self._download_image(url, path)

    def _download_image(self, url, path):
        """
        Download the image from the given URL to the specified path.
        
        Parameters:
        - url (str): The URL of the image.
        - path (str): The local file path to save the image.
        """
        response = requests.get(url)
        if response.status_code == 200:
            with open(path, 'wb') as f:
                f.write(response.content)

    
    def _get_image_features(self, route, bearings):
        """
        Get the image features from Mapillary using the interface API.
        
        Parameters:
        - route: List of (lat, lon) tuples
        - bearings: List of bearings corresponding to each route point
        
        Returns:
        - image_features: List of cleaned image features
        - sequence_ids: Dictionary of sequence_id frequencies
        """
        image_features = []
        sequence_ids = {}
        search_radius_meters = 10

        for (lat, lon), bearing in zip(route, bearings):
            try:
                # Search for images with specific fields and parameters
                search_results = mly.interface.get_image_close_to(
                    longitude=lon,
                    latitude=lat,
                    radius=search_radius_meters,
                    fields=['id', 'compass_angle', 'sequence_id'],  # Only request needed fields
                    image_type='flat'  # Exclude panoramic images
                )

                if not hasattr(search_results, 'features'):
                    continue

                # Process features for this route point
                point_features = []
                for feature in search_results.features:
                    props = feature.properties
                    
                    # Get required properties with fallbacks
                    img_id = getattr(props, 'id', None)
                    img_heading = getattr(props, 'compass_angle', None)
                    seq_id = getattr(props, 'sequence_id', None)

                    if not all([img_id, img_heading, seq_id]):
                        continue

                    # Check if image heading matches route bearing
                    heading_diff = abs(img_heading - bearing)
                    if heading_diff <= 45 or heading_diff >= 315:
                        image_feature = {
                            'id': img_id,
                            'heading': img_heading,
                            'coordinates': (lat, lon),
                            'sequence_id': seq_id
                        }
                        point_features.append(image_feature)
                        sequence_ids[seq_id] = sequence_ids.get(seq_id, 0) + 1

                image_features.append(point_features)

            except Exception as e:
                print(f"Error at coordinates ({lat}, {lon}): {str(e)}")
                continue

        return image_features, sequence_ids
    
    def _clean_image_features(self, image_features, sequence_ids):
        """
        Clean the list of image features by:
        
        1. Removing duplicates (by 'id'), only keeping the first occurrence.
        2. Grouping features by their (lat, lon) to identify "per-route-point" groups.
        3. For each route point group, picking the sequence_id(s) that has the highest
        frequency across the entire route (using sequence_ids dict).
        4. Keeping only the features belonging to that 'best' sequence_id (or IDs in case of a tie).
        
        Parameters
        ----------
        image_features : list of list of dict
            A list of image feature dictionaries, each containing:
                ['id' (str), 'heading' (float), 'coordinates' (tuple), 'sequence_id' (str)]
        sequence_ids : dict
            A dictionary mapping sequence_id -> frequency (int) in the entire route.
        
        Returns
        -------
        cleaned_features : list of dict
            The cleaned list of image features.
        """

        if not image_features or not sequence_ids:
            return []

        
        seen_ids = set()
        unique_features = []
        for feat in image_features:
            point_image_features = []
            for f in feat:
                id = f['id']
                if id not in seen_ids:
                    # Step 1: Remove duplicates by image 'id', keep the first occurrence
                    point_image_features.append(f)
                    seen_ids.add(id)
            unique_features.append(point_image_features)    

        # 3. Keep only features whose sequence_id has that max frequency
        cleaned_features = []
        for feat in unique_features:
            max_freq = 0
            feat_to_add = None
            for f in feat:
                seq_id = f['sequence_id']
                total_num_images = sequence_ids[seq_id]
                if total_num_images > max_freq:
                    max_freq = total_num_images
                    feat_to_add = f
            if feat_to_add:
                cleaned_features.append(feat_to_add)

        return cleaned_features


