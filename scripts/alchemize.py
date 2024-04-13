import whisper
import os
import re
import tomllib


def validate_app_config(app_dic):            
    # model_dir
    if not isinstance(app_dic['model_dir'], str):
        raise ValueError("model_dir must be a string")
    if not os.path.isdir(app_dic['model_dir']):
        raise FileNotFoundError("model_dir directory does not exist")
    
    # recordings_dir
    if not isinstance(app_dic['recordings_dir'], str):
        raise ValueError("recordings_dir must be a string")
    if not os.path.isdir(app_dic['recordings_dir']):
        raise FileNotFoundError("recordings_dir directory does not exist")

    # pending_dir
    if not isinstance(app_dic['pending_dir'], str):
        raise ValueError("pending_dir must be a string")
    if not os.path.isdir(app_dic['pending_dir']):
        raise FileNotFoundError("pending_dir directory does not exist")

     # rename_to_dir
    if not isinstance(app_dic['renamed_dir'], str):
        raise ValueError("renamed_dir must be a string")
    if not os.path.isdir(app_dic['renamed_dir']):
        raise FileNotFoundError("renamed_dir directory does not exist")

    # move_if_rename_fail
    if not isinstance(app_dic['move_unsupported'], bool):
        raise ValueError("move_unsupported must be a boolean (True/False)")

    if app_dic['move_unsupported']: # if the move is true we need to check rename_failed_dir
        if not isinstance(app_dic['unsupported_dir'], str):
            raise ValueError("unsupported_dir must be a string")
        if not os.path.isdir(app_dic['unsupported_dir']):
            raise FileNotFoundError("unsupported_dir directory does not exist")

    # verbose_mode
    if not isinstance(app_dic['verbose'], bool):
        raise ValueError("verbose must be a boolean (True/False)")

    # words_in_name
    if not isinstance(app_dic['max_words'], int):
        raise ValueError("max_words must be an integer")
    if not 0 < app_dic['max_words'] <= 20:  # Assuming a reasonable range
        raise ValueError("max_words must be between 1 and 20")

    return;


def validate_sort_config(sort_dic):

    return;


def load_config(config_file):
    with open(config_file, 'rb') as file:
        config_dic = tomllib.load(file)
    # check validity
    if 'app' not in config_dic.keys():
        print('app section not in config, exiting...')
        exit()
    
    variable_names = [
    "model_dir",
    "recordings_dir",
    "pending_dir",
    "renamed_dir",
    "move_unsupported",
    "unsupported_dir",
    "verbose",
    "max_words",
    ]

    missing_vars = [var for var in variable_names if var not in config_dic['app']]
    if missing_vars:  # Check if any variables are missing
        print(f"The following variables are missing under [app] in config: {', '.join(missing_vars)}")
        print("Exiting...")
        exit()

    validate_app_config(config_dic['app'])
    validate_sort_config(config_dic['sort'])
    return config_dic
    

def safe_rename(from_name, to_name, add_count=False, verbose = True):
    """
    Renames a file safely, adding a numeric suffix if the destination already exists.

    Args:
        from_name: The path to the file to rename.
        to_name: The desired new name for the file.
        add_count: A boolean flag indicating whether to add a numeric suffix if the destination exists.

    Returns:
        The renamed file path, or None if the rename failed.
    """

    if not os.path.exists(from_name):
        print(f"File '{from_name}' does not exist. Skipping rename.")
        return None

    if os.path.exists(to_name):
        if not add_count:
            print(f"File '{to_name}' already exists. Skipping rename.")
            return None
        else:
            # Add a numeric suffix to avoid overwriting
            base, ext = os.path.splitext(to_name)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}") and i < 100:
                i += 1
            to_name = f"{base}_{i}{ext}"

            if i == 100:
                print(f"File '{to_name}' already exists and has to many duplicates. Skipping rename.\n")
                return None

    os.rename(from_name, to_name)
    if verbose:
        print(f"Renamed '{from_name}' to '{to_name}'.\n")
    return to_name



def get_first_words(in_audio_file, download_model_dir, max_words):
    model = whisper.load_model("large", download_root=download_model_dir)

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
    last_word_index = min(max_words, len(first_words))
    return first_words[:last_word_index]

def rename_files(app_dic):
    #name dic will be a double dicitionary to save the naming data
    name_dic = {}

    '''                       yy      mm     dd     tttt   cnt       ext     '''
    sony_format_pattern = r'(\d{2})(\d{2})(\d{2})_(\d{4})(_\d{2})?\.(mp3|wav)' #TODO magic values mp3 and wav

    # get all audio files in the convert dir and extract information saving to the name_dic
    for file_name in os.listdir(app_dic['pending_dir']):
        file_path = os.path.join(app_dic['pending_dir'], file_name)

        if file_name.lower().endswith((".mp3", ".wav")):  # TODO magic values mp3 and wav
            if app_dic['verbose']:
                print(f'Working on file: {file_name}', flush=True)

            match = re.match(sony_format_pattern, file_name)

            if match:
                yy, mm, dd, tttt, _, ext = match.groups()
                ext = ext.lower()
                first_words = '-'.join(
                    get_first_words(
                        file_path, 
                        app_dic['model_dir'],
                        app_dic['max_words']))
            else:
                if app_dic['verbose']:
                    print(f'file is not in one of the naming formats supported\n' + \
                          f'No rename for: {file_name}\n')
            
                if app_dic['move_unsupported']:
                    if app_dic['verbose']:
                        print(f'Moving to {app_dic['unsupported_dir']}')
                    safe_rename(
                        os.path.join(app_dic['pending_dir'], file_name),
                        os.path.join(app_dic['unsupported_dir'], file_name), 
                        add_count = True, verbose = app_dic['verbose'])
                continue

            new_file_name = (
                f'20{yy}-{mm}-{dd}_{tttt}_' +
                ('empty' if first_words == '' else f'{first_words}') +
                f'.{ext}')
        
            safe_rename(
                os.path.join(app_dic['pending_dir'], file_name),
                os.path.join(app_dic['renamed_dir'], new_file_name),
                add_count = True, verbose = app_dic['verbose'])
            
            
            # this is to ease sorting
            name_dic[file_name] = {'yy': yy, 'mm': mm, 'dd': dd, 'tttt': tttt, 'ext': ext}
            name_dic[file_name]['words'] = first_words
    return name_dic


if __name__ == '__main__':
    config_file = './scripts/config.toml'  #TODO add other config file locations to check; currently this is only setup for docker
    config = load_config(config_file)
    if config['app']['verbose']:
        print('Successfully loaded config\n')

    rename_files(config['app'])
