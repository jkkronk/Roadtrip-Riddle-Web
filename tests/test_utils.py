from utils import get_expiration_time, calculate_score, is_valid_username
import unittest
import pytz
from datetime import datetime, time, timedelta

class TestUtils(unittest.TestCase):
    def test_before_0500(self):
        expiration_datetime = get_expiration_time()
        now = datetime.now(pytz.timezone('Europe/Brussels'))
        expiration_time = time(5, 0, 0)
        expected_datetime = datetime.combine(now.date(), expiration_time, tzinfo=pytz.timezone('Europe/Brussels'))
        if now.time() > expiration_time:
            expected_datetime += timedelta(days=1)
        assert expiration_datetime == expected_datetime

    #  Calculate score for a video with time taken less than video duration
    def test_calculate_score_less_than_duration(self):
        time_taken = 20
        video_file_path = "./tests/data/quiz.mp4"
        expected_score = 72
        actual_score = calculate_score(time_taken, video_file_path)

        assert actual_score == expected_score

    #  Calculate score for a video with time taken more than video duration
    def test_calculate_score_equal_to_duration(self):
        time_taken = 100
        video_file_path = "./tests/data/quiz.mp4"
        expected_score = 0

        actual_score = calculate_score(time_taken, video_file_path)

        assert actual_score == expected_score

    def test_valid_username(self):
        assert is_valid_username("abc123") == True
        assert is_valid_username("1234567890") == True
        assert is_valid_username("a1b2c3d4e5f6g7h8i9j0") == True
        assert is_valid_username("abc!@#") == False
        assert is_valid_username("abc_123") == True
        assert is_valid_username("qwerty$%^") == False
        assert is_valid_username("123 456") == False
        assert is_valid_username("AbC dEf") == False
        assert is_valid_username("!@#$%^&*()") == False
        assert is_valid_username("") == False
        assert is_valid_username("Aa") == True
        assert is_valid_username("qwertyuiopasdfghjklzxcv") == False
        assert is_valid_username("AbCdEfGhIjKlMnOpQrStUvWxYz") == False

