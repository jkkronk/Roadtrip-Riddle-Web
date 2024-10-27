from pydantic import BaseModel, Field
import json

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
