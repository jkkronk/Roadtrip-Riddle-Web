from openai import AsyncOpenAI
from pathlib import Path
from tempfile import NamedTemporaryFile
import asyncio
from pydub import AudioSegment
import os
import requests
import io
from quiz.quiz_clues import QuizCluesWithAudio
async def generate_audio_chunk(client, voice, chunk, nr):
    """
    Generate audio for a chunk of text.
    :param client: client
    :param voice: what voice to use
    :param chunk: chunk of text
    :param nr: nr of chunk
    :return:
    """
    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=chunk
    )
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_file_path = temp_file.name  # Get the file path
        response.stream_to_file(temp_file_path)  # Use the file path here
    chunk_audio = AudioSegment.from_mp3(temp_file_path)  # Use the file path to load the audio
    # Optionally delete the temporary file if needed
    os.remove(temp_file_path)
    return chunk_audio


async def quiz_2_speech_openai(quiz, voice, openai_api_key=""):
    """
    Generate audio for a quiz.
    :param quiz: quiz class
    :param voice: what voice to use
    :param openai_api_key: api key
    :return:
    """
    if openai_api_key == "":
        client = AsyncOpenAI()
    else:
        client = AsyncOpenAI(api_key=openai_api_key)

    speech_file_path = Path(__file__).parent / "speech.mp3"

    print(f"Generating audio for voice {voice}, to file {speech_file_path}")

    chunks = [clue for clue in quiz.clues]

    # make sure that each chunk is less than 4000 characters, otherwise split the chunk in two entries
    while any([len(chunk) > 4000 for chunk in chunks]):
        new_chunks = []
        for chunk in chunks:
            if len(chunk) > 4000:
                new_chunks.append(chunk[:4000])
                new_chunks.append(chunk[4000:])
            else:
                new_chunks.append(chunk)
        chunks = new_chunks

    tasks = []
    for nr, chunk in enumerate(chunks):
        tasks.append(generate_audio_chunk(client, voice, chunk, nr))
    chunk_audios = await asyncio.gather(*tasks)

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    for chunk_audio in chunk_audios:
        concatenated_audio += chunk_audio
        concatenated_audio += AudioSegment.silent(duration=500)

        # Export concatenated audio to a file
        with NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
            temp_file_path = temp_file.name  # Get the file path
            concatenated_audio.export(temp_file_path, format="mp3")
            # read audio file and return raw bytes
            with open(temp_file_path, "rb") as f:
                raw_audio_bytes = f.read()

    return concatenated_audio


async def text_2_speech_openai(text, voice, openai_api_key=""):
    """
    Generate audio for a text.
    :param text: text to generate audio for
    :param voice: what voice to use
    :param openai_api_key: api key
    :return:
    """
    if openai_api_key == "":
        client = AsyncOpenAI()
    else:
        client = AsyncOpenAI(api_key=openai_api_key)

    speech_file_path = Path(__file__).parent / "speech.mp3"

    print(f"Generating audio for voice {voice}, to file {speech_file_path}")

    chunks = [text]

    # make sure that each chunk is less than 4000 characters, otherwise split the chunk in two entries
    while any([len(chunk) > 4000 for chunk in chunks]):
        new_chunks = []
        for chunk in chunks:
            if len(chunk) > 4000:
                new_chunks.append(chunk[:4000])
                new_chunks.append(chunk[4000:])
            else:
                new_chunks.append(chunk)
        chunks = new_chunks

    tasks = []
    for nr, chunk in enumerate(chunks):
        tasks.append(generate_audio_chunk(client, voice, chunk, nr))
    chunk_audios = await asyncio.gather(*tasks)

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    for chunk_audio in chunk_audios:
        concatenated_audio += chunk_audio

        # Export concatenated audio to a file
        with NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
            temp_file_path = temp_file.name  # Get the file path
            concatenated_audio.export(temp_file_path, format="mp3")
            # read audio file and return raw bytes
            with open(temp_file_path, "rb") as f:
                raw_audio_bytes = f.read()

    return concatenated_audio


def quiz_2_speech_elevenlabs(text, voice_id, api_key):
    """
    Convert the quiz clues to speech using ElevenLabs API.
    :param text: text to convert to speech
    :param voice_name: Name of the voice to use
    :param api_key: Your ElevenLabs API key
    :return: AudioSegment object containing the speech audio
    """
    
    # Prepare the request to ElevenLabs API
    headers = {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': api_key,
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
        headers=headers,
        json=data
    )
    
    # Check for errors in the response
    if response.status_code != 200:
        raise Exception(f"ElevenLabs API request failed with status code {response.status_code}: {response.text}")
    
    # Load the audio content
    audio = AudioSegment.from_file(io.BytesIO(response.content), format="mp3")
    return audio


def create_audio(city_quiz, use_elevenlabs=False, elevenlabs_api_key=''):
    """
    Create the audio file for the quiz using either OpenAI or ElevenLabs API.
    """
    # Cast the QuizClues to QuizCluesWithAudio
    city_quiz_with_audio = QuizCluesWithAudio(
        clues=city_quiz.clues,
        explanations=city_quiz.explanations,
        introduction=city_quiz.introduction
    )
    
    host_voice = "X2j354mOfDROQk9ghjz4"
    
    for round in range(city_quiz_with_audio.get_nr_rounds()):
        print(f"Generating audio for round {round}")
        text = city_quiz_with_audio.get_clue(round)
        if use_elevenlabs:
            sound = quiz_2_speech_elevenlabs(text, host_voice, elevenlabs_api_key)
        else:
            sound = asyncio.run(quiz_2_speech_openai(text, host_voice))
        city_quiz_with_audio.append_clue_sound(sound)
    
    return city_quiz_with_audio