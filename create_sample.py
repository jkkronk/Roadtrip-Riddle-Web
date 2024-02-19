import argparse
import os
from quiz import quiz_creator, street_view_collector, video_creator

'''
Create a mobile version sample. Used to create a sample quiz and video for the mobile version of the quiz.
'''
def main():
    parser = argparse.ArgumentParser(description='Create a new quiz.')
    parser.add_argument('out', type=str, help='The folder to use for the quiz.')
    parser.add_argument('city', type=str, help='What destination to use for the quiz.')

    args = parser.parse_args()

    quiz_creator.create_new_quiz("./data", args.city)
    street_view_collector.create_new_frames("./data", "mobile")
    video_creator.create_new_video("./data", args.out)


if __name__ == "__main__":
    main()