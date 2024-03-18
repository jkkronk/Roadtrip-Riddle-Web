import math
import google_streetview.api
import requests
import polyline
import numpy as np
from io import BytesIO
from PIL import Image, ImageFilter
import os
import pickle


def add_logo_on_top(image, logo_path="./data/logo.png"):
    """
    Add the logo on top of the image
    :param image: Background image to add the logo on top of
    :return: Image with the logo on top
    """

    logo = Image.open(logo_path)
    logo_width, logo_height = logo.size
    # Resize the logo to be a bit smaller than the width of the first image in the list
    base_width, base_height = image.size
    logo_width = min(base_width - 20, logo_width)  # Adjust 20 to the desired smaller size
    logo_height = int((logo_width / logo.size[0]) * logo.size[1])
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)

    images_with_logo = []
    position = ((base_width - logo_width) // 2, (base_height // 3) - (logo_height // 3))

    # Paste the top image on the base image
    image.paste(logo, position, logo)

    return image


def calculate_heading(lat1, lng1, lat2, lng2):
    """
    Calculate the heading between two points
    :param lat1: latitude of the first point
    :param lng1: longitude of the first point
    :param lat2: latitude of the second point
    :param lng2: longitude of the second point
    :return: heading in degrees
    """
    # Convert degrees to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    # Calculate the change in coordinates
    delta_lng = lng2 - lng1

    # Calculate the heading
    x = math.sin(delta_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(delta_lng))
    heading = math.atan2(x, y)

    # Convert heading to degrees and adjust to compass heading
    heading = math.degrees(heading)
    heading = (heading + 360) % 360
    return heading


def duration_to_num_points(duration, image_duration=0.4, extra_duration=10):
    """
    Calculate the number of points to use based on the duration of the video
    :param duration: duration of the video
    :param image_duration: duration of each image
    :param extra_duration: add extra duration to the video to allow for the car to stop at the destination
    :return: number of points to use
    """
    num_points = int((duration + extra_duration) / image_duration)
    return num_points


def get_path_coordinates(destination, start_location="", num_points=10, api_key=""):
    """
    Get the coordinates of the path from the start location to the destination
    :param destination: destination city
    :param start_location: start location if "" then a random location is chosen 10 km from the destination
    :param num_points: number of points to use
    :param api_key: google api key
    :return: list of coordinates
    """
    if api_key == "":
        api_key = os.environ.get('GOOGLE_API_KEY')

    destination_coord = get_coordinates_from_city(destination)

    if (start_location == ""):
        # Randomly generate a start location in a ring around the destination
        # Earth radius in kilometers
        R = 6371.0
        lat1 = np.radians(destination_coord[0])
        lon1 = np.radians(destination_coord[1])
        bearing = np.radians(np.random.uniform(0, 360))
        d_radians = 15 / R # 10 km from the destination
        new_lat = np.arcsin(np.sin(lat1) * np.cos(d_radians) +
                            np.cos(lat1) * np.sin(d_radians) * np.cos(bearing))
        new_lon = lon1 + np.arctan2(np.sin(bearing) * np.sin(d_radians) * np.cos(lat1),
                                    np.cos(d_radians) - np.sin(lat1) * np.sin(new_lat))

        new_lat_deg = np.degrees(new_lat)
        new_lon_deg = np.degrees(new_lon)

        start_coord = new_lat_deg, new_lon_deg
    else:
        start_coord = get_coordinates_from_city(start_location)

    print(f"Coordinates: Start at {start_coord} Finish at {destination_coord}")

    # Set up the request to the Google Directions API
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        'origin': f'{start_coord[0]},{start_coord[1]}',
        'destination': f'{destination_coord[0]},{destination_coord[1]}',
        'key': api_key
    }

    # Make the request
    response = requests.get(base_url, params=params)
    # print(response.json())
    if response.status_code != 200:
        raise ConnectionError("Failed to connect to the Directions API")

    if response.json()['status'] != "OK":
        print("Direction status: " + response.json()['status'])
        return []
    directions = response.json()

    # Extract the polyline from the first route
    encoded_polyline = directions['routes'][0]['overview_polyline']['points']

    # Decode the polyline
    full_path = polyline.decode(encoded_polyline)

    # Select evenly spaced points from the path
    path_coordinates = []
    for i in range(0, min(num_points, len(full_path))):
        path_coordinates.append(full_path[i])

    # Trim or extend the list to match the desired number of points
    if len(path_coordinates) > num_points:
        path_coordinates = path_coordinates[:num_points]
    if len(path_coordinates) < num_points:
        print("Not enough points in the path. Only got " + str(len(path_coordinates)) + " points.")
        return []

    return path_coordinates


def fetch_street_view_images(path_coordinates, image_path="", view="mobile", api_key="", crop_bottom=True, add_logo=False, width_full=-1, height_full=-1):
    """
    Fetch the street view images for the given path coordinates
    :param path_coordinates: path coordinates
    :param image_path: path to save the images
    :param view: mobile or desktop
    :param api_key: google api key
    :param crop_bottom: crop the bottom of the image
    :param add_logo: add a logo on top of the image
    :param width_full: width of the image
    :param height_full: height of the image
    :return:
    """
    if api_key == "":
        api_key = os.environ.get('GOOGLE_API_KEY')

    size = "640x640" if view == "mobile" else "630x400"

    if image_path != "":
        frames_folder = os.path.join(image_path, 'frames')

        # Check if the frames folder exists, and create it if it doesn't
        if not os.path.exists(frames_folder):
            os.makedirs(frames_folder)

    images = []
    for i in range(len(path_coordinates) - 1):
        print(f"Fetching image {i + 1} of {len(path_coordinates) - 1}")
        lat, lng = path_coordinates[i]
        next_lat, next_lng = path_coordinates[i + 1]

        # Calculate heading towards the next point
        heading = calculate_heading(lat, lng, next_lat, next_lng)

        params = [{
            "size": size,  # Image size
            "fov": "120",  # Field of view
            "radius": "100",  # How far away from the location to capture
            "location": f"{lat},{lng}",
            "heading": heading,  # Adjust if needed to face the direction of the path
            "pitch": "0",
            "source": "outdoor",  # Outdoor images only
            "key": api_key
        }]
        results = google_streetview.api.results(params)

        # Download the image
        response = requests.get(results.links[0])

        if response.status_code == 200:
            image_data = response.content

            if not is_gray_image(image_data):
                image = Image.open(BytesIO(image_data))

                if crop_bottom:
                    width, height = image.size
                    pixels = 30
                    image = image.crop((0, 0, width, height - pixels))
                if add_logo:
                    image = add_logo_on_top(image)
                if width_full != -1 and height_full != -1:
                    image = add_boarder(image, width_full, height_full)

                if image_path != "":
                    image.save(os.path.join(frames_folder, f"{i}.jpg"))
                # Append opencv image to list
                images.append(np.array(image))
    return images



def get_coordinates_from_city(city):
    """
    Get the coordinates of a city
    :param city: city name
    :return: returns the latitude and longitude of the city
    """
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': city,
        'format': 'json'
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        result = response.json()
        if result:
            return float(result[0]['lat']), float(result[0]['lon'])
        else:
            raise ValueError("No results found for the given city.")
    else:
        raise ConnectionError("Failed to connect to the Nominatim API.")


def is_gray_image(image_path):
    """
    Check if the image is predominantly gray.
    @param image_path: path to the image
    """
    image = Image.open(BytesIO(image_path))
    np_image = np.array(image)

    # Calculate the standard deviation of the color channels
    std_dev = np_image.std(axis=(0, 1))
    return all(x < 20 for x in std_dev)  # Threshold for grayness, might need adjustment


def create_new_frames(data_dir="/var/data", video_format="desktop", width=-1, height=-1):
    """
    Create new frames
    :param data_dir: path to the data directory
    :param video_format: mobile or desktop
    :param width: width of the video
    :param height: height of the video
    :return: void
    """
    with open(os.path.join(data_dir, "path_coordinates.pkl"), "rb") as f:
        path_coordinates = pickle.load(f)
    # Check if there is more than 100 files in the frames folder
    frames_path = os.path.join(data_dir, "frames")
    # Check if the frames folder exists, and create it if it doesn't
    if not os.path.exists(frames_path):
        os.makedirs(frames_path)

    itr = 0
    nbr_files = 0
    while nbr_files < len(path_coordinates) * 0.5:
        fetch_street_view_images(path_coordinates, data_dir, video_format, width_full=width, height_full=height)
        nbr_files = len(os.listdir(os.path.join(data_dir, "frames")))
        # if we have done this 10 times and still have less than 100 files, then we have a problem
        itr += 1
        if itr > 10:
            raise Exception("Failed to create frames")


def add_boarder(frame, final_width, final_height):
    '''
    Add a border to the frame. If the image is smaller than 2/3 of the final size, then the image is resized to fit the final size.
    @param frame:
    @param final_width:
    @param final_height:
    @return:
    '''
    final_image = Image.new("RGB", (final_width, final_height), "black")
    blurred_background = frame.resize((final_width, final_height)).filter(ImageFilter.GaussianBlur(15))
    frame = frame.resize((int(final_width*2/3), int(final_height*2/3)))
    frame_width, frame_height = frame.size
    border_width = (final_width - frame_width) // 2
    border_height = (final_height - frame_height) // 2
    final_image.paste(blurred_background, (0, 0))
    final_image.paste(frame, (border_width, border_height))
    return final_image
