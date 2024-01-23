import os.path
import pickle
from pydantic import BaseModel, Field
from openai import OpenAI
import instructor
import json
import random
import asyncio

from quiz import street_view_collector
from quiz import audio_creator

class QuizHost():
    intro: str = Field(..., description="The introduction of the quiz.")
    outro: str = Field(..., description="The outro of the quiz.")

    #init
    def __init__(self, intro, outro):
        self.intro = intro
        self.outro = outro

class QuizClues(BaseModel):
    clues: list[str] = Field(..., description="A list of size 5 with clues for the quiz.")
    explanations: list[str] = Field(..., description="A list of size 5 with explanations for the clues.")

    def clear_city(self):
        self.clues = [clue.replace("Zurich", "the city") for clue in self.clues]

    def get_clue(self, round: int) -> str:
        return self.clues[round]

    def get_explanation(self, round: int) -> str:
        return self.explanations[round]

    def get_all_clues(self):
        return "\n".join(self.clues)

    def get_all_explanation(self) -> str:
        return "\n".join(self.explanations)

    def save(self, city, file_path: str):
        data = {
            "city": city,
            "clues": self.clues,
            "explanations": self.explanations
        }
        with open(file_path, 'w') as file:
            json.dump(data, file)

    @classmethod
    def open(cls, file_path: str):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return cls(clues=data['clues'], explanations=data['explanations'])

def random_destination(data_path) -> str:
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


def create_new_quiz(data_dir="/var/data/", city=""):
    path_coordinates = []
    while len(path_coordinates) == 0:
        # Create a new quiz
        if city == "":
            city = random_destination(data_dir)
        city_quiz = create_quiz(city)
        #city_quiz = QuizClues.open("static/quiz.json")
        city_quiz.save(city, os.path.join(data_dir, "quiz.json"))

        # Create the audio
        host_voice = "echo"
        sound = asyncio.run(audio_creator.quiz_2_speech_openai(city_quiz, host_voice))
        host = QuizHost("What city is our destination?...", f"... And the correct answer is... {city}")
        sound_intro = asyncio.run(audio_creator.text_2_speech_openai(host.intro, host_voice))
        sound = sound_intro + sound
        sound.export(os.path.join(data_dir, "quiz.mp3"), format="mp3")
        #sound = AudioSegment.from_mp3("static/quiz.mp3")

        # Create the video
        duration = sound.duration_seconds
        num_points = street_view_collector.duration_to_num_points(duration, extra_duration=10) # 10 extra seconds

        for i in range(50):
            print(f"Attempt {i} to get a path with {num_points} points")
            # Try to get a path with the correct number of points
            path_coordinates = street_view_collector.get_path_coordinates(city, "", num_points)
            print(f"Got {len(path_coordinates)} points")
            if len(path_coordinates) == num_points:
                break

    with open(os.path.join(data_dir,"path_coordinates.pkl"), "wb") as f:
        pickle.dump(path_coordinates, f)
