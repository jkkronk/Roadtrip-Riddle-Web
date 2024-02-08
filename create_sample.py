import argparse
import os
from quiz import quiz_creator, street_view_collector, video_creator


def main():
    parser = argparse.ArgumentParser(description='Create a new quiz.')
    parser.add_argument('out', type=str, help='The folder to use for the quiz.')
    parser.add_argument('intro', type=str, help='Path to an optional intro to the quiz.')

    args = parser.parse_args()

    # If there is a args.info file, use it as the intro.
    if args.intro is None:
        intro = ""
    else:
        with open(args.intro, "r") as file:
            intro = file.read()

    city = quiz_creator.create_new_quiz("./data", additional_intro=intro)
    street_view_collector.create_new_frames("./data", "mobile")
    video_creator.create_new_video("./data", args.out)
    video_creator.add_destination_to_video(os.path.join(args.out, "quiz.mp4"), city, True)
    video_creator.add_background_to_video(os.path.join(args.out, "quiz_with_destination.mp4"), city)


if __name__ == "__main__":
    main()