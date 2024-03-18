from openai import OpenAI, AsyncOpenAI
from elevenlabs import generate
from pathlib import Path
from tempfile import NamedTemporaryFile
import asyncio
from pydub import AudioSegment
import os
import io
from moviepy.editor import AudioFileClip

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


def quiz_2_speech_elevenlabs(quiz, intro=None, outro=None):
    '''
    Generate audio for a quiz.
    @param quiz: Main quiz object
    @param intro: intro text
    @param outro: outro text
    @return: voice audio
    '''
    print(f"Generating audio to file")

    chunks = [clue for clue in quiz.clues]

    concatenated_audio = AudioSegment.empty()
    if intro:
        chunk_audio = generate(text=intro, voice="jUlmiWjCqIf6U3aP5jsd", model="eleven_multilingual_v2")
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment

    for index, chunk in enumerate(chunks):
        chunk_audio = generate(text=chunk, voice="jUlmiWjCqIf6U3aP5jsd", model="eleven_multilingual_v2")
        # Assuming that the generate function represents mp3
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment

    if outro:
        chunk_audio = generate(text=outro, voice="jUlmiWjCqIf6U3aP5jsd", model="eleven_multilingual_v2")
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment

    temp_file = "temp_audio.mp3"
    concatenated_audio.export(temp_file, format="mp3")
    audio = AudioFileClip(temp_file)
    os.remove(temp_file)
    return audio
