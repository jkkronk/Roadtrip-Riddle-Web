import os.path
from pydantic import Field
from openai import OpenAI
import instructor
import asyncio

from quiz import audio_creator
from quiz.quiz_clues import QuizClues
from quiz.utils import random_destination


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
                The clues should get harder and harder to guess. In the beginning it should be hard. 
                In the end it should be very easy.
                
                Additionally, add a short explanation for each clue.
                
                An example for the destination Paris could be:
                >>Road Trip Riddle Time! Where are we going?...
                >>First Clue: We head towards the city of light or should I say the capital of light? The city is home to the world's most visited museum...
                >>Second Clue: In our destination a tower reaches for the sky and lovers lock promises on a bridge...
                >>Third Clue: Amidst cafes and boulevards, our destination is the heart of a nation famed for romance and revolution...
                >>Fourth Clue: In this city, pair is not the name of the dame. It's Notre...
                >>Last Clue: We have arrived to the city where a famous tower reaches the sky, and painters love to gather. Here, you can say 'bonjour' and enjoy a croissant by the river...

                Another example for Beijing could be:
                >>Road Trip Riddle Time! Where are we going?...
                >>First Clue: We head towards a heavenly city in a country where tea flows like rivers and pearls shine like stars...
                >>Second Clue: We end up in a square that echoes with both past whispers and future strides, under the watchful eyes of a Chairman...
                >>Third Clue: Do we end with jing? Yes, and in our local language it also means capital...
                >>Fourth Clue: Seek a city where ducks are famously roasted. The duck even has it's own Birdsnest at our destination...
                >>Last Clue:  "ni hao" We have now arrived in an asian capital where giant pandas play in a land far away...
                
                Another example for Mumbai could be:
                >>Road Trip Riddle Time! Where are we going?...
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


def create_quiz_files(data_dir="/var/data/", quiz_name="quiz.json", city=""):
    """
    Create a new quiz. Saves the quiz, the audio to given data directory.
    :param data_dir: path to the data directory
    :param city: city name
    :return:
    """
    
    # If no city is provided, get a random city
    if city == "":
        city = random_destination(data_dir)

    # Create a new quiz
    city_quiz = create_quiz(city)
    #city_quiz = QuizClues.open("static/quiz.json")
    quiz_path = os.path.join(data_dir, quiz_name)
    city_quiz.save(city, quiz_path)

    # Create the audio
    host_voice = "echo"
    sound_name = quiz_name.replace(".json", ".mp3")
    sound = asyncio.run(audio_creator.quiz_2_speech_openai(city_quiz, host_voice))
    sound.export(os.path.join(data_dir, sound_name), format="mp3")

    return data_dir
    