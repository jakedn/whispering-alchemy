import whisper
import os
import re


# Global Configurations
''' This is the directory to save whisper models to '''
model_dir = '/app/model'

''' Directory where all recordings are held '''
recordings_dir = '/app/recordings_dir'

''' Directory where the files are to be renamed '''
rename_from_dir = '/app/recordings_dir/intake-pending-rename'

''' Directory to move the renamed files to'''
rename_to_dir = '/app/recordings_dir/intake-pending-sort'

''' If true we move files that we couldn't rename, otherwise it stays put unchanged '''
move_if_rename_fail = True

''' Directory to move all the files that failed to rename. If move_if_rename_fail is false this does nothing '''
rename_failed_dir = '/app/recordings_dir/intake-pending-rename/pending-manual-rename'

''' Should the be verbose '''
verbose_mode = True

''' Defines the maximum words that should be in the renaming of a file; this refers to the word extraction from the audio file '''
words_in_name = 4


def get_first_words(in_audio_file):
    model = whisper.load_model("large", download_root=model_dir)

    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(in_audio_file)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio, n_mels=128).to(model.device)

    # detect the spoken language
    #_, probs = model.detect_language(mel)
    #print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions(fp16 = False, language="en")
    result = whisper.decode(model, mel, options)

    # limit to first words_in_name words
    first_words = re.findall(r'\b[\w\',]+\b', result.text)
    last_word_index = min(words_in_name, len(first_words))
    return first_words[:last_word_index]

if __name__ == '__main__':
    ''' name dic will be a double dicitionary to save the naming data '''
    name_dic = {}

    '''                       yy      mm     dd     tttt        ext     '''
    sony_format_pattern = r'(\d{2})(\d{2})(\d{2})_(\d{4})\.(mp3|wav)' #TODO magic values mp3 and wav

    # get all audio files in the convert dir and extract information saving to the name_dic
    for file_name in os.listdir(rename_from_dir):
        file_path = os.path.join(rename_from_dir, file_name)
        if file_name.lower().endswith((".mp3", ".wav")):  # TODO magic values mp3 and wav
            if verbose_mode == True:
                print(f'Working on file: {file_name}', flush=True)
            match = re.match(sony_format_pattern, file_name)
            if match:
                yy, mm, dd, tttt, ext = match.groups()
                ext = ext.lower()
                first_words = '-'.join(get_first_words(file_path))
            else:
                yy, mm, dd, tttt, ext = None, None, None, None, None
                first_words = ''

            name_dic[file_name] = {'yy': yy, 'mm': mm, 'dd': dd, 'tttt': tttt, 'ext': ext}
            name_dic[file_name]['words'] = first_words


    for file_name in name_dic.keys():
        #TODO transcribe based on specific keywords

        # rename audio file
        data_dic = name_dic[file_name]

        if data_dic['words'] == '':
            data_dic['words'] = 'empty'

        if data_dic['yy'] == None:
            if verbose_mode:
                print(f'file is not in one of the naming formats supported\n' + \
                      f'No rename for: {file_name}')
            
            if move_if_rename_fail:
                if verbose_mode:
                    print(f'Moving to {rename_failed_dir}')
                os.rename(
                    os.path.join(rename_from_dir, file_name),
                    os.path.join(rename_failed_dir, file_name)
                )
        else:
            new_file_name = f'20{data_dic["yy"]}' + \
                            f'-{data_dic["mm"]}' + \
                            f'-{data_dic["dd"]}' + \
                            f'_{data_dic["tttt"]}' + \
                            f'_{data_dic["words"]}' + \
                            f'.{data_dic["ext"]}'
            os.rename(
                os.path.join(rename_from_dir, file_name),
                os.path.join(rename_to_dir, new_file_name)
            )