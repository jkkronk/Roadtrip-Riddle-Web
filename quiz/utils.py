import os
import random
from pydub import AudioSegment
def random_destination(path_to_cities="./static/cities.txt") -> str:
    """
    Get a random destination from the cities text file.
    :param data_path: path to the cities text file
    :return: city name
    """
    # Opening the file
    with open(path_to_cities, 'r') as file:
        cities_text = file.read()

    # Splitting the text into a list of cities
    cities_list = cities_text.split(',')

    # Selecting a random city from the list
    random_city = random.choice(cities_list)
    return random_city.replace("\n", "")

def get_mp3_file_length(file_path: str) -> float:
    """
    Get the length of an mp3 file.
    :param file_path: path to the mp3 file
    :return: length of the mp3 file
    """
    return AudioSegment.from_mp3(file_path).duration_seconds