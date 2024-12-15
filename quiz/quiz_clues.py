from pydantic import BaseModel, Field
import json
from pydub import AudioSegment
import base64
import io
import os

class QuizClues(BaseModel):
    """
    A class that represents the clues for a quiz.
    """
    introduction: str = Field(..., description="The introduction for the quiz.")
    clues: list[str] = Field(..., description="A list of size 5 with clues for the quiz.")
    explanations: list[str] = Field(..., description="A list of size 5 with explanations for the clues.")

    def clear_city(self, city: str):
        """
        Replace the city name with "the city" in all clues.
        :return:
        """
        self.clues = [clue.replace(city, "the city") for clue in self.clues]

    def get_introduction(self) -> str:
        """
        Get the introduction.
        :return:
        """
        return self.introduction

    def get_clue(self, round: int) -> str:
        """
        Get the clue for a specific round.
        :param round:
        :return:
        """
        if round == 0:
            return self.introduction
        else:
            return self.clues[round-1]

    def get_explanation(self, round: int) -> str:
        """
        Get the explanation for a specific round.
        :param round:
        :return:
        """
        return self.explanations[round]

    def get_nr_rounds(self) -> int:
        """
        Get the number of rounds.
        :return:
        """
        return len(self.clues) + 1

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
            "introduction": self.introduction,
            "clues": self.clues,
            "explanations": self.explanations,
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
            return cls(
                introduction=data['introduction'],
                clues=data['clues'], 
                explanations=data['explanations'],
            )
    
   
class QuizCluesWithAudio(QuizClues):
    """
    A class that represents the clues for a quiz with audio.
    """
    model_config = {"arbitrary_types_allowed": True}
    
    clues_sound: list[AudioSegment] = []
    pause_duration: float = 1.5
    
    def append_clue_sound(self, clue_sound: AudioSegment):
        """
        Add a clue sound to the list of clue sounds.
        :param clue_sound:
        :return:
        """
        self.clues_sound.append(clue_sound)

    def get_clue_sound(self, round: int) -> AudioSegment:
        """
        Get the clue sound for a specific round.
        :param round:
        :return:
        """
        return self.clues_sound[round+1]

    def get_total_duration(self) -> float:
        """
        Get the total duration of the audio file.
        :return:
        """
        return self.get_complete_audio().duration_seconds
    
    def get_complete_audio(self) -> AudioSegment:
        """
        Get the all the clues sound as a single audio file.
        :return:
        """
        # Start with 1ms of silence (minimal duration to avoid crossfade error)
        sound = AudioSegment.silent(duration=1)
        for idx, clue in enumerate(self.clues_sound):
            if idx == 0:
                sound = clue + AudioSegment.silent(duration=int(self.pause_duration * 100))
            else:
                sound = sound + clue + AudioSegment.silent(duration=int(self.pause_duration * 500))
        return sound

    @classmethod
    def open(cls, file_path: str):
        """
        Open a json file with clues and explanations.
        :param file_path: path to the json file
        :return:
        """
        with open(file_path, 'r') as file:
            data = json.load(file)
            return cls(
                introduction=data['introduction'],
                clues=data['clues'], 
                explanations=data['explanations'], 
                clues_sound=[AudioSegment.from_mp3(sound_path) for sound_path in data['clues_sound']]
            )

    def save(self, city, file_path: str):
        """
        Save the clues and explanations to a json file.
        :param city: city name
        :param file_path: path to the json file
        :return: void
        """
        # Create audio directory next to the json file
        audio_dir = os.path.join(os.path.dirname(file_path), 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Save audio files and collect their paths
        audio_paths = []
        for i, sound in enumerate(self.clues_sound):
            audio_path = os.path.join(audio_dir, f'clue_{i}.mp3')
            sound.export(audio_path, format="mp3")
            audio_paths.append(audio_path)

        data = {
            "city": city,
            "introduction": self.introduction,
            "clues": self.clues,
            "explanations": self.explanations,
            "clues_sound": audio_paths
        }
        with open(file_path, 'w') as file:
            json.dump(data, file)