import os.path
import pickle
from pydantic import BaseModel, Field
from openai import OpenAI
import instructor
import json
import random
import asyncio
from moviepy.editor import AudioFileClip
from pydub import AudioSegment

from quiz import street_view_collector
from quiz import audio_creator
from quiz import video_creator
class QuizHost():
    """
    A class that represents a quiz host.
    """
    intro: str = Field(..., description="The introduction of the quiz.")
    outro: str = Field(..., description="The outro of the quiz.")

    #init
    def __init__(self, intro, outro):
        self.intro = intro
        self.outro = outro

class QuizClues(BaseModel):
    """
    A class that represents the clues for a quiz.
    """
    clues: list[str] = Field(..., description="A list of size 5 with clues for the quiz.")
    explanations: list[str] = Field(..., description="A list of size 5 with explanations for the clues.")

    def clear_city(self):
        """
        Replace the city name with "the city" in all clues.
        :return:
        """
        self.clues = [clue.replace("Zurich", "the city") for clue in self.clues]

    def get_clue(self, round: int) -> str:
        """
        Get the clue for a specific round.
        :param round:
        :return:
        """
        return self.clues[round]

    def get_explanation(self, round: int) -> str:
        """
        Get the explanation for a specific round.
        :param round:
        :return:
        """
        return self.explanations[round]

    def get_all_clues(self):
        """
        Get all the clues as a string.
        :return:
        """
        return "\n".join(self.clues)

    def get_all_explanation(self) -> str:
        """
        Get all the explanations as a string.
        :return:
        """
        return "\n".join(self.explanations)

    def save(self, city, file_path: str):
        """
        Save the clues and explanations to a json file.
        :param city: city name
        :param file_path: path to the json file
        :return: void
        """
        data = {
            "city": city,
            "clues": self.clues,
            "explanations": self.explanations
        }
        with open(file_path, 'w') as file:
            json.dump(data, file)

    @classmethod
    def open(cls, file_path: str):
        """
        Open a json file with clues and explanations.
        :param file_path: path to the json file
        :return:
        """
        with open(file_path, 'r') as file:
            data = json.load(file)
            return cls(clues=data['clues'], explanations=data['explanations'])

def random_destination(data_path) -> str:
    """
    Get a random destination from the cities text file.
    :param data_path: path to the cities text file
    :return: city name
    """

    # open the cities text file and pick a random city
    # return the city
    path_to_cities = os.path.join("./static", "cities.txt")

    # Opening the file
    with open(path_to_cities, 'r') as file:
        cities_text = file.read()

    # Splitting the text into a list of cities
    cities_list = cities_text.split(',')

    # Selecting a random city from the list
    random_city = random.choice(cities_list)

    return random_city.replace("\n", "")

def create_quiz(city:str, openai_api_key="") -> QuizClues:
    """
    Create a quiz for a city.
    :param city: city name
    :param openai_api_key: openai api key
    :return:
    """
    if openai_api_key == "":
        client = instructor.patch(OpenAI())
    else:
        client = instructor.patch(OpenAI(api_key=openai_api_key))

    prompt = f"""
                You are a quiz host and you are hosting a quiz where the answer is {city}. You are suppose to come up
                with 5 clues for the city. Each clue should be easier and easier. In the beginning it 
                shall be very hard. But in the end it shall be very easy. 
                
                Each clue should be one or two sentences long. 
                The clues should be written in English. 
                The clues could be on historic facts, famous persons, famous buildings, famous events, famous food, 
                famous drinks, famous music, famous art, famous sports, famous games, famous movies, famous books, from 
                {city}. 
                Each clue should end with "..."
                The clues can be humorous and like a riddle. There can be word plays, rimes and puns.
                The clues should get harder and harder to guess. In the beginning it should be very hard. 
                But in the end it should be very easy.
                
                Additionally, add a short explanation for each clue.
                
                An example for the destination Paris could be:
                >>First Clue: We head towards the city of light or should I say the capital of light? The city is home to the world's most visited museum...
                >>Second Clue: In our destination a tower reaches for the sky and lovers lock promises on a bridge...
                >>Third Clue: Amidst cafes and boulevards, our destination is the heart of a nation famed for romance and revolution...
                >>Fourth Clue: In this city, pair is not the name of the dame. It's Notre...
                >>Last Clue: We have arrived to the city where a famous tower reaches the sky, and painters love to gather. Here, you can say 'bonjour' and enjoy a croissant by the river...
                
                Another example for Beijing could be:
                >>First Clue: We head towards a heavenly city in a country where tea flows like rivers and pearls shine like stars...
                >>Second Clue: We end up in a square that echoes with both past whispers and future strides, under the watchful eyes of a Chairman...
                >>Third Clue: Do we end with jing? Yes, and in our local language it also means capital...
                >>Fourth Clue: Seek a city where ducks are famously roasted. The duck even has it's own Birdsnest at our destination...
                >>Last Clue:  "ni hao" We have now arrived in an asian capital where giant pandas play in a land far away...
                
                Another example for Mumbai could be:
                >>First Clue: We head towards the Gateway of the country. The city traffic doesn't stop the Dabbawalas delivering...
                >>Second Clue: Vada pav, the city name sandwich, Pani Puri, Khaman. The street food is a delight but watch out for the spice...
                >>Fourth Clue: At our destination Bollywood is the name of the game. The city is home to the largest film industry in the world...
                >>Third Clue: Our destination is bustling and breaming, and cricket is like a religion...
                >>Last Clue: Bomb the bay! No! It's new name is Mmmmmm...
                """


    clues: QuizClues = client.chat.completions.create(
        model="gpt-4",
        response_model=QuizClues,
        messages=[
            {"role": "user", "content": prompt},
        ],
        max_retries=2,
    )

    return clues


def create_new_quiz(data_dir="/var/data/", city="", add_outro=False, num_points=300):
    """
    Create a new quiz.
    :param data_dir: path to the data directory
    :param city: city name
    :return:
    """
    # Create a new quiz
    if city == "":
        city = random_destination(data_dir)
    print("Creating a new quiz for", city)
    city_quiz = create_quiz(city)

    # Create the audio
    intro = "Vart är vi på väg?..."
    outro = f"Och vi har kommit fram till... {city}..."
    audio = audio_creator.quiz_2_speech_elevenlabs(city_quiz, intro, outro)

    # Create the video
    print("Creating the video")
    path_coordinates = street_view_collector.get_path_coordinates(city, "", num_points)
    images = street_view_collector.fetch_street_view_images(path_coordinates, view="mobile")
    print("... Frames to video")
    output_data = os.path.join(data_dir, f"{city}.mp4")
    video_creator.images_to_video(output_data, images, audio)
    print("-----Done!-----")
