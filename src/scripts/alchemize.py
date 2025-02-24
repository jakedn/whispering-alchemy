import os
import sys
import re
import datetime
import argparse
import whisper
import json

models = "/model-dir"


def get_first_words(audio_file_in, model_dir_in, max_words, trans_language = "en", model_name="base"):

    #TODO make config for the rename model to be used so its not hardcoded
    model = whisper.load_model(model_name, download_root=model_dir_in)

    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio_file_in)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    if not model_name.endswith(".en"):
        # detect the spoken language
        _, probs = model.detect_language(mel)
        lang_guess = max(probs, key=probs.get)
        if args.verbose:
            if lang_guess != trans_language:
                print(f"Detected language: {lang_guess}\nWARNING!: It differs from the input language: {trans_language}", file = sys.stderr)
            else:
                print(f"Detected language: {lang_guess}", file = sys.stderr)

    elif args.verbose:
        print(f"Model with '.en', no detecting language.", file = sys.stderr)
        if trans_language != 'en':
            print(f"WARNING!: using .en model with non en input language:", file = sys.stderr)

    #TODO decode in dedected language?

    # decode the audio
    options = whisper.DecodingOptions(fp16 = False, language=trans_language)
    result = whisper.decode(model, mel, options)

    # limit to first words_in_name words
    first_words = re.findall(r'\b[\w\',]+\b', result.text)
    last_word_index = min(max_words, len(first_words))
    return first_words[:last_word_index]


def get_transcription(audio_file_in, model_dir_in, trans_language = "en", model_name = "base.en"):

    result = ''

    model = whisper.load_model(model_name, download_root=model_dir_in)
    # audio = whisper.load_audio(audio_file_in)
    # audio = whisper.pad_or_trim(audio)
    # # make log-Mel spectrogram and move to the same device as the model
    # mel = whisper.log_mel_spectrogram(audio, n_mels=128).to(model.device)

    # # decode the audio
    # options = whisper.DecodingOptions(fp16 = False, language="en")
    # result = whisper.decode(model, mel, options)

    transcription_res = model.transcribe(audio_file_in, fp16 = False, language=trans_language)
    result = transcription_res

    return result


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Transcribe audio files using Whisper.")
    parser.add_argument("--audio-file-ext", dest="audio_ext", default="mp3", help="Path to the audio file")
    parser.add_argument("--get-words", dest="get_words", type=int, default=4, help="Number of first words to get; this defaults to first 30 seconds of recording")
    parser.add_argument("--lang", type=str, default="en", help="Language of transcription")
    parser.add_argument("--output", type=str, default="text", help="output type")
    parser.add_argument("--model", type=str, default="base", 
                        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large", "turbo"], 
                        help="Whisper model (base, small, medium, large...)")
    parser.add_argument("--words-model", dest="words_model", type=str, default="tiny", 
                        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large", "turbo"],
                        help="Whisper model (base, small, medium, large...)")
    parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")

    args = parser.parse_args()

    start_time = datetime.datetime.now()
    if args.verbose:
        print(f'\nStarted running script: {start_time}', file = sys.stderr)

    # copy file to transcribe
    with open(f"/app/tmp/audio.{args.audio_ext}", 'wb') as output_file: # open in binary mode
            while True:
                chunk = sys.stdin.buffer.read(4096)  # Read in chunks (4KB)
                if not chunk:
                    break  # End of input
                output_file.write(chunk)

    audio_file = f"/app/tmp/audio.{args.audio_ext}"

    # get name
    if args.output == "words":
        words = get_first_words(audio_file, models, args.get_words, args.lang, args.words_model)
        print(words)
    else:
        # get transcription
        trans = get_transcription(audio_file, models, args.lang, args.model)

        if args.output == "text":
            print(trans["text"])
        elif args.output == "json":
            json.dump(trans, sys.stdout, indent=2)
        else:
            print("bad output mode")
            exit(1)


    if args.verbose:
        print(f'\nFinished running script: {datetime.datetime.now()}\nTime elapsed: {datetime.datetime.now() - start_time}', file=sys.stderr)
