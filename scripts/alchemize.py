import os
import re
import tomllib
import shutil
import datetime

DEACTIVATE_TRANSCRIBE = False
try:
    import whisper
except ImportError:
    DEACTIVATE_TRANSCRIBE = True


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

    # pending_rename_dir
    if not isinstance(app_dic['pending_rename_dir'], str):
        raise ValueError("pending_rename_dir must be a string")
    if not os.path.isdir(app_dic['pending_rename_dir']):
        raise FileNotFoundError("pending_rename_dir directory does not exist")

     # rename_to_dir
    if not isinstance(app_dic['pending_sort_dir'], str):
        raise ValueError("pending_sort_dir must be a string")
    if not os.path.isdir(app_dic['pending_sort_dir']):
        raise FileNotFoundError("pending_sort_dir directory does not exist")

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


def load_config():
    config_exits = False
    config_options = ['./config/config.toml', './scripts/config.toml']
    for config_path in config_options:
        if os.path.exists(config_path):
            config_exits = True
            config_file_path = config_path
            break
    if not config_exits:
        print("no config found, exiting...")
        exit(1)

    with open(config_file_path, 'rb') as file:
        config_dic = tomllib.load(file)
    # check validity
    if 'app' not in config_dic.keys():
        print('app section not in config, exiting...')
        exit()
    
    variable_names = [
    "model_dir",
    "recordings_dir",
    "pending_rename_dir",
    "pending_sort_dir",
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
    return config_dic
    

def get_file_types(in_file_types, return_type = "list"):
    ext_list = []

    # remove leading '.' if they are present
    for file_ext in in_file_types:
        if file_ext[0] == '.':
            ext_list.append(file_ext[1:])
        else:
            ext_list.append(file_ext)

    if return_type == "list":
        return ext_list

    elif return_type == "tuple":
        return tuple(ext_list)

    elif return_type == "regex":
        return '|'.join(ext_list)
    
    else:
        print("unknown return type")
        exit(1)


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
        if verbose:
            print(f"File '{from_name}' does not exist. Skipping rename.")
        return None

    if os.path.exists(to_name):
        if not add_count:
            if verbose:
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
                if verbose:
                    print(f"File '{to_name}' already exists and has to many duplicates. Skipping rename.")
                return None

    shutil.move(from_name, to_name)
    if verbose:
        print(f"Renamed '{from_name}' to '{to_name}'")
    return to_name


def get_first_words(audio_file_in, model_dir_in, max_words):
    global current_transcriptions

    current_transcriptions += 1
    model = whisper.load_model("large", download_root=model_dir_in)

    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio_file_in)
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


def get_transcription(audio_file_in, model_dir_in, model_mode_in = "large"):
    global current_transcriptions
    result = ''

    # if transcription file exists we will take the transcription from the existing txt file
    transcription_file = f'{audio_file_in}.{model_mode_in}.txt'
    if os.path.exists(transcription_file):
        with open(transcription_file, "r") as file:
            result = file.read()
        return result
    
    if DEACTIVATE_TRANSCRIBE:
        print("WARNING! trying to transcribe when transcription disabled! transcription left blank")
        return result

    current_transcriptions += 1
    model = whisper.load_model(model_mode_in, download_root=model_dir_in)
    # audio = whisper.load_audio(audio_file_in)
    # audio = whisper.pad_or_trim(audio)
    # # make log-Mel spectrogram and move to the same device as the model
    # mel = whisper.log_mel_spectrogram(audio, n_mels=128).to(model.device)

    # # decode the audio
    # options = whisper.DecodingOptions(fp16 = False, language="en")
    # result = whisper.decode(model, mel, options)

    transcription_res = model.transcribe(audio_file_in, fp16 = False)
    result = transcription_res['text']

    return result


def rename_files(app_dic):
    global max_transcriptions
    global current_transcriptions
    #name dic will be a double dicitionary to save the naming data
    name_dic = {}

    file_ext_reg_str = get_file_types(app_dic["convertible_extensions"], "regex")
    file_ext_tuple = get_file_types(app_dic["convertible_extensions"], "tuple")

    '''                       yy      mm     dd     tttt   cnt       ext     '''
    sony_format_pattern = r'(\d{2})(\d{2})(\d{2})_(\d{4})(_\d{2})?\.(' + file_ext_reg_str + r')$'

    # get all audio files in the convert dir and extract information saving to the name_dic
    for file_name in os.listdir(app_dic['pending_rename_dir']):
        if max_transcriptions <= current_transcriptions:
            print(f'got to the max transcriptions, no more transcribing')
            return name_dic
        
        file_path = os.path.join(app_dic['pending_rename_dir'], file_name)

        if file_name.lower().endswith(file_ext_tuple):
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
                        os.path.join(app_dic['pending_rename_dir'], file_name),
                        os.path.join(app_dic['unsupported_dir'], file_name), 
                        add_count = True, verbose = app_dic['verbose'])
                    print('\n', end = '')
                continue

            new_file_name = (
                f'20{yy}-{mm}-{dd}_{tttt}_' +
                ('empty' if first_words == '' else f'{first_words}') +
                f'.{ext}')
        
            safe_rename(
                os.path.join(app_dic['pending_rename_dir'], file_name),
                os.path.join(app_dic['pending_sort_dir'], new_file_name),
                add_count = True, verbose = app_dic['verbose'])
            print('\n', end = '')
            
            # this is to ease sorting
            name_dic[file_name] = {'yy': yy, 'mm': mm, 'dd': dd, 'tttt': tttt, 'ext': ext}
            name_dic[file_name]['words'] = first_words
    return name_dic


def add_to_logseq(logseq_dir, file_path, name_dic):
    return;


def sort_files(config_in):
    app_config = config_in['app']

    file_ext_reg_str = get_file_types(app_config["convertible_extensions"], "regex")

    file_name_pattern = r'(\d{4})-(\d{2})-(\d{2})(_(\d{4}))?_(.*).(' + file_ext_reg_str + r')$'
    
    for file_name in os.listdir(app_config['pending_sort_dir']):
        match = re.match(file_name_pattern, file_name)
        if not match:
            if app_config['verbose']:
                print(f'filename: {file_name} is not in a supported format to sort, please sort manually.')
            continue
        groups = match.groups()
        name_dic = {
            'yy': groups[0], 
            'mm': groups[1], 
            'dd': groups[2], 
            'tttt': groups[4], 
            'words': groups[5].split('-')
            }
        file_path = os.path.join(app_config['pending_sort_dir'], file_name)
        
        #todo custom sorting logic that is independant of using logseq; maybe there should be two functions logseq sorting and file sorting.

        # logseq sorting
        logseq_config = config['logseq']
        if logseq_config['enable']:
            logseq_asset_dir = os.path.join(logseq_config['logseq_dir'], 'assets/voicenotes')
            logseq_journal_dir = os.path.join(logseq_config['logseq_dir'], 'journals')
            
            tags = logseq_config['tags']

            found_keyword = False
            for tag in tags.keys():
                curr_tag = tags[tag]

                for keyword in curr_tag['keywords']:
                    if ' '.join(name_dic['words']).lower()[:len(keyword)] == keyword:
                        found_keyword = True
                        break

                if found_keyword:
                    logseq_file = f"{name_dic['yy']}_{name_dic['mm']}_{name_dic['dd']}.md"

                    # add spacing if the journal already exists for aestetics 
                    file_spacing = '\n-\n- ' if os.path.exists(os.path.join(logseq_journal_dir, logseq_file)) else ''
            
                    # tag of the found keyword
                    tag_name = f'[[{curr_tag['tag_str']}]] ' if curr_tag['tag_str'] != '' else ''
                    
                    # get transcription
                    trans_str = ('\n    - ' + get_transcription(file_path, app_config['model_dir'], logseq_config['logseq_model_mode'])) if curr_tag['transcribe'] else ''
                    if len(trans_str) > logseq_config['max_transcription_len']:
                        if app_config['verbose']:
                            print(f'file: {file_name} has a trasnscription of more then {logseq_config['max_transcription_len']} characters, skipping transcription')
                        trans_str = ''

                    with open(os.path.join(logseq_journal_dir, logseq_file), "a") as file:
                        file.write(
                            f'{file_spacing}{tag_name}[[validate whisper]]' +
                            f'\n    - ![voice recording](../assets/voicenotes/{file_name})' + 
                            trans_str)
                    
                    rename_result = safe_rename(file_path, os.path.join(logseq_asset_dir, file_name), verbose=app_config['verbose'])
                    
                    if rename_result is None:
                        print(f"'{file_name}' was not able to be moved to the logseq asset folder, make sure you fix manually!")

                    if app_config['verbose']:
                        print(f"Added '{file_name}' link to logseq journal '{logseq_file}'\n")

                    break


def transcribe_files(config_in):
    global max_transcriptions
    global current_transcriptions

    app_config = config_in['app']
    file_ext_list = get_file_types(app_config["convertible_extensions"], "list")

    transcribe_dir_list = [dir for dir in app_config['pending_transcribe_dirs']]
    transcribe_dir_list.append(app_config['pending_sort_dir'])
    for transcribe_dir in transcribe_dir_list:
        if app_config['verbose']:
            print(f"\nWorking in directory '{transcribe_dir}'")
        if not os.path.exists(transcribe_dir):
            print(f"directory '{transcribe_dir}' does not exist or is not mounted. skipping...")
            continue

        for file_name in os.listdir(transcribe_dir):
            if max_transcriptions <= current_transcriptions:
                print(f'got to the max transcriptions, no more transcribing')
                return ;
            
            if app_config['verbose']:
                print(f"Working on file '{file_name}'", flush=True)

            file_path = os.path.join(transcribe_dir, file_name)
            _, file_name_ext =  os.path.splitext(file_name)

            new_file_name = f'{file_name}.{app_config['transcribe_model_mode']}.txt'
            new_file_path = os.path.join(transcribe_dir, new_file_name)

            if os.path.exists(new_file_path):
                if app_config['verbose']:
                    print(f"file '{file_name}' has transcription txt file. skipping...")
                continue

            # check file extention
            if file_name_ext[1:] not in file_ext_list:
                if app_config['verbose']:
                    print(f"'{file_name}' does not have a convertible extension as per the configuration file, skipping...")
                continue

            # get transcription
            trans_str = get_transcription(file_path, app_config['model_dir'], app_config['transcribe_model_mode'])

            with open(new_file_path, "w") as file:
                file.write(trans_str)
            
            if app_config['verbose']:
                print(f"transcribed file '{file_name}'")


if __name__ == '__main__':
    config = load_config()

    if config['app']['verbose']:
        print(f'\nStarted running script: {datetime.datetime.now()}')

    if config['app']['disable_transcribe']:
        DEACTIVATE_TRANSCRIBE = True
        print("Transcriptions DISABLED!")

    global max_transcriptions
    global current_transcriptions
    current_transcriptions = 0
    max_transcriptions = config['app']['transcribe_limit']
    if max_transcriptions == 0:
        max_transcriptions = 100

    if config['app']['verbose']:
        print(f'Max transcriptions set to {max_transcriptions}')
        print('Successfully loaded config\n')
        print('Start renaming files')
    if not DEACTIVATE_TRANSCRIBE:
        rename_files(config['app'])
    else:
        if config['app']['verbose']:
            print('skipping rename because transcribing is not active')

    if config['app']['verbose']:
        print('Finished renaming files')
        print('\nStart manual transcriptions')
    if not DEACTIVATE_TRANSCRIBE:
        transcribe_files(config)
    else:
        if config['app']['verbose']:
            print('skipping transcribe because transcribing is not active')

    if config['app']['verbose']:
        print('Fininished manual transcriptions')
        print('\nStart sorting files')
    sort_files(config)

    if config['app']['verbose']:
        print('Finished sorting files')

    if config['app']['verbose']:
        print(f'\nFinished running script: {datetime.datetime.now()}')
