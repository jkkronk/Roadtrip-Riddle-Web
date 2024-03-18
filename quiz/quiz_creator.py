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
                shall be very hard. But in the end it shall be very easy. The Quiz should be in Swedish.
                
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
                
                An example for the destination New York could be:
                >>10 Poäng... Vi reser mot stad där världens mest kända fabrik en gång låg. Rickard III:s hus är liksom Fedora och Fez ledtrådar till resmålet där Ruth var stadens babe en gång i tiden...
                >>8 Poäng... 24/7 och 24/10 kan på olika sätt förknippas med resmålet som Liza Minelli sjöng om 1977...
                >>6 Poäng... Celticanatagonister är en dubbel ledtråd till staden där brevmannen hade en sen show. Jonagold ger er lite ny information till Jake LaMottas allt annat än måttfulla stad...
                >>4 Poäng... Skyskraporna börjar torna upp sig i horisonten i vår östkustsstad där UNHCR, WHO och UNICEF har sina säten och där US Airways Flight 1549 gjorde en spektakulär landning...
                >>2 Poäng... Vi är nu framme i USA:s största stad och nju ska du få dom avslutande ledtrådarna till vårt 2-delade resmål. Frihetsgudinnan, Empire State Building, Broadway och Manhattan...
                
                Another example for Berlin could be:
                >>10 Poäng... Vi lämnar röd folkmördares fru och åker med pendeltåg till stad som lyfter upp blåblommig nyttoväxt...
                >>8 Poäng... Ta en lugn stund under vanligt parkträd så köpe nick en munk när vi är framme...
                >>6 Poäng... Isbjörnar och Fredrika Bremer litteratur tillhör inte världseliten men staden är ändå världens snabbaste både på kort och lång distans. Bravo Charlie!...
                >>4 Poäng... Vi är på väg mot historisk mark både ekonomisk och världspolitisk. Mustaschprydd diktator avslutade i staden vars mest kända byggnadsverk pryds av fyra hästar. Bran den burgen ner?...
                >>2 Poäng...  Jag ber Linn att servera blåBER, LINgon och dönerkebab. Vi är nu framme i huvudstaden som en gång  var delad i öst och väst...
                
                Another example for Zurich could be:
                >>10 Poäng... 230 volt ger er startplatsen för denna resa men nu tar vi liksom briljanta briljantjägare sikte på broderande boplats...
                >>8 Poäng... Vi svissar nu fram i vacker omgivning men historiskt sett är vi inte långt från helvetet. Solens läge mitt på dagen, randig häst och polska pengar är inte urdum information...
                >>6 Poäng... I denna stad har man en röst i och om det mesta och här har både Einstein och Lenin varit bosatta. Och i vår världsstad prater man grannlandets språk och de säger visst att jag avslutar...
                >>4 Poäng... En av världens största börser finns i staden vars namn skvallrar om att det är en rik stad vi söker. Och banka nu in att ABB:s huvudkontor ligger här liksom chokladtillverkaren Lindt...
                >>2 Poäng... I denna finansstad inte långt från Alperna syr ich, förlåt jag ihop många affärer...
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


def create_new_quiz(data_dir="/var/data/", city="", add_outro=False):
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
    audio = audio_creator.quiz_2_speech_elevenlabs(city_quiz, "Vart är vi på väg?...", f"Och vi har kommit fram till... {city}...")

    num_points = int(audio.duration * 24 + 100) # 24 frames per second. 100 frames extra

    # Collecting frames
    print(f"Collecting {num_points} # street view images...")
    path_coordinates = street_view_collector.get_path_coordinates(city, num_points=num_points)
    print(f"Collected {len(path_coordinates)} coordinates")
    images = street_view_collector.fetch_street_view_images(path_coordinates, view="mobile")

    # Create the video
    print(f"Collected {len(images)} frames. Creating video...")
    video_creator.images_to_video(os.path.join(data_dir, f"{city}.mp4"), images, audio)
    print("-----Done!-----")
