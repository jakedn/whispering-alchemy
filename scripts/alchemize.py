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


def verbose_print(in_str):
    global app_config

    if app_config['verbose']:
        print(in_str)


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

    # consumer_dir
    if not isinstance(app_dic['consumer_dir'], str):
        raise ValueError("consumer_dir must be a string")
    if not os.path.isdir(app_dic['consumer_dir']):
        raise FileNotFoundError("consumer_dir directory does not exist")

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
    config_options = [os.path.expanduser('~/.config/whispering-alchemy/config.toml'),
                                         './config/config.toml', 
                                         './scripts/config.toml']
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
    "consumer_dir",
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
        return r'\.(' + '|'.join(ext_list) + r')$'
    
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
                print(f"File '{to_name}' already exists and has to many duplicates. Skipping rename.")
                return None

    shutil.move(from_name, to_name)
    if verbose:
        print(f"Renamed '{from_name}' to '{to_name}'")
    return to_name


def get_first_words(audio_file_in, model_dir_in, max_words, model="medium.en"):
    global current_transcriptions

    current_transcriptions += 1
    #TODO make config for the rename model to be used so its not hardcoded
    model = whisper.load_model(model, download_root=model_dir_in)

    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio_file_in)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

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


def rename_files():
    global max_transcriptions
    global current_transcriptions
    global app_config
    #name dic will be a double dicitionary to save the naming data
    name_dic = {}

    file_ext_reg_str = get_file_types(app_config["convertible_extensions"], "regex")
    file_ext_tuple = get_file_types(app_config["convertible_extensions"], "tuple")

    '''                       yy      mm     dd     tttt   cnt       ext     '''
    sony_format_pattern = r'(\d{2})(\d{2})(\d{2})_(\d{4})(_\d{2})?' + file_ext_reg_str

    # get all audio files in the convert dir and extract information saving to the name_dic
    rename_file_list = [ f for f in os.listdir(app_config['consumer_dir']) if f.lower().endswith(file_ext_tuple) ]
    for file_name in rename_file_list:
        if max_transcriptions <= current_transcriptions:
            print(f'got to the max transcriptions, no more transcribing')
            return name_dic
        
        file_path = os.path.join(app_config['consumer_dir'], file_name)

        verbose_print(f'Working on file: {file_name}', flush=True)

        match = re.match(sony_format_pattern, file_name)

        if match:
            yy, mm, dd, tttt, _, ext = match.groups()
            ext = ext.lower()
            first_words = '-'.join(
                get_first_words(
                    file_path, 
                    app_config['model_dir'],
                    app_config['max_words']))
        else:
            verbose_print(f'file is not in one of the naming formats supported\nNo rename for: {file_name}\n')
        
            if app_config['move_unsupported']:
                verbose_print(f'Moving to {app_config['unsupported_dir']}')
                safe_rename(
                    os.path.join(app_config['consumer_dir'], file_name),
                    os.path.join(app_config['unsupported_dir'], file_name), 
                    add_count = True, verbose = app_config['verbose'])
                print('\n', end = '')
            continue

        new_file_name = (
            f'20{yy}-{mm}-{dd}_{tttt}_' +
            ('empty' if first_words == '' else f'{first_words}') +
            f'.{ext}')
    
        safe_rename(
            os.path.join(app_config['consumer_dir'], file_name),
            os.path.join(app_config['pending_sort_dir'], new_file_name),
            add_count = True, verbose = app_config['verbose'])
        print('\n', end = '')
        
        # this is to ease sorting
        name_dic[file_name] = {'yy': yy, 'mm': mm, 'dd': dd, 'tttt': tttt, 'ext': ext}
        name_dic[file_name]['words'] = first_words
    return name_dic


def add_to_logseq(logseq_dir, file_path, name_dic):
    return;


def transcribe_files():
    global max_transcriptions
    global current_transcriptions
    global app_config

    file_ext_tuple = get_file_types(app_config["convertible_extensions"], "tuple")

    transcribe_dir_list = [dir for dir in app_config['pending_transcribe_dirs']]
    transcribe_dir_list.append(app_config['pending_sort_dir'])
    for transcribe_dir in transcribe_dir_list:
        verbose_print(f"\nWorking in directory '{transcribe_dir}'")
        if not os.path.exists(transcribe_dir):
            print(f"directory '{transcribe_dir}' does not exist or is not mounted. skipping...")
            continue
        trans_file_list = [ f for f in os.listdir(transcribe_dir) if f.lower().endswith(file_ext_tuple) ]
        for file_name in trans_file_list:
            if max_transcriptions <= current_transcriptions:
                print(f'got to the max transcriptions, no more transcribing')
                return ;
            
            verbose_print(f"Working on file '{file_name}'", flush=True)

            file_path = os.path.join(transcribe_dir, file_name)
            _, file_name_ext =  os.path.splitext(file_name)

            new_file_name = f'{file_name}.{app_config['transcribe_model_mode']}.txt'
            new_file_path = os.path.join(transcribe_dir, new_file_name)

            if os.path.exists(new_file_path):
                verbose_print(f"file '{file_name}' has transcription txt file. skipping...")
                continue

            # get transcription
            trans_str = get_transcription(file_path, app_config['model_dir'], app_config['transcribe_model_mode'])

            with open(new_file_path, "w") as file:
                file.write(trans_str)
            
            verbose_print(f"transcribed file '{file_name}'")


def sort_files():
    global config_dic
    global app_config
    model_mode = app_config['transcribe_model_mode']

    file_ext_reg_str = get_file_types(app_config["convertible_extensions"], "regex")
    file_ext_tuple = get_file_types(app_config["convertible_extensions"], "tuple")

    file_name_pattern = r'(\d{4})-(\d{2})-(\d{2})(_(\d{4}))?_(.*)' + file_ext_reg_str
    
    sort_file_list = [ f for f in os.listdir(app_config['pending_sort_dir']) if f.lower().endswith(file_ext_tuple) ]
    for file_name in sort_file_list:
        match = re.match(file_name_pattern, file_name)
        if not match:
            verbose_print(f'filename: {file_name} is not in a supported format to sort, please sort manually.')
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
        # file based sorting
        sort_config = config_dic['sorting']
        sort_model_mode = model_mode
        if sort_config['enable']:
            folders = sort_config['folder']
            found_keyword = False
            for folder in folders.keys():
                curr_folder = folders[folder]

                for keyword in curr_folder['keywords']:
                    if ' '.join(name_dic['words']).lower()[:len(keyword)] == keyword:
                        found_keyword = True
                        break

                if found_keyword:
                    new_dir = curr_folder['dir']
                    if not os.path.exists(new_dir):
                        print(f"directory '{new_dir}' does not exist, skipping file '{file_name}'")
                        break
                    new_file_path = os.path.join(new_dir, file_name)
                    rename_res = safe_rename(file_path, new_file_path, verbose= app_config['verbose'])
                    if rename_res is not None:
                        safe_rename(f'{file_path}.{sort_model_mode}.txt', f'{new_file_path}.{sort_model_mode}.txt', verbose= app_config['verbose'])
                    break
            if found_keyword:
                continue

        # logseq sorting
        logseq_config = config_dic['logseq']
        logseq_model_mode = logseq_config['logseq_model_mode']
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
                    block_prefix = '\n-\n- ' if os.path.exists(os.path.join(logseq_journal_dir, logseq_file)) else '- '
            
                    # tag of the found keyword
                    tag_name = f'[[{curr_tag['tag_str']}]] ' if curr_tag['tag_str'] != '' else ''
                    
                    # get transcription
                    trans_str = ('\n    - ' + get_transcription(file_path, app_config['model_dir'], logseq_model_mode)) if curr_tag['transcribe'] else ''
                    if len(trans_str) > logseq_config['max_transcription_len']:
                        verbose_print(f'file: {file_name} has a trasnscription of more then {logseq_config['max_transcription_len']} characters, skipping transcription')
                        trans_str = ''

                    with open(os.path.join(logseq_journal_dir, logseq_file), "a") as file:
                        #TODO create entry in logseq config for the intake tag so mine isnt hard codded
                        file.write(
                            f'{block_prefix}{tag_name}[[📨validate whisper]]' +
                            f'\n    - ![voice recording](../assets/voicenotes/{file_name})' + 
                            trans_str)
                    
                    rename_result = safe_rename(file_path, os.path.join(logseq_asset_dir, file_name), verbose=app_config['verbose'])
                    
                    if rename_result is None:
                        print(f"'{file_name}' was not able to be moved to the logseq asset folder, make sure you fix manually!")
                    else:
                        safe_rename(f'{file_path}.{logseq_model_mode}.txt', f'{file_path}.{logseq_model_mode}.txt.used')
                    verbose_print(f"Added '{file_name}' link to logseq journal '{logseq_file}'\n")

                    break


if __name__ == '__main__':
    global config_dic
    global app_config
    config_dic = load_config()
    app_config = config_dic['app']

    start_time = datetime.datetime.now()
    verbose_print(f'\nStarted running script: {start_time}')

    if app_config['disable_transcribe']:
        DEACTIVATE_TRANSCRIBE = True
        print("Transcriptions DISABLED!")

    global max_transcriptions
    global current_transcriptions
    current_transcriptions = 0
    max_transcriptions = app_config['transcribe_limit']
    if max_transcriptions == 0:
        max_transcriptions = 100

    verbose_print(f'''Max transcriptions set to {max_transcriptions}
only converting files with extentions: {', '.join(get_file_types(app_config["convertible_extensions"], "list"))}
Successfully loaded config\n'
Start renaming files''')

    if not DEACTIVATE_TRANSCRIBE:
        rename_files()
    else:
        verbose_print('skipping rename because transcribing is not active')

    verbose_print('Finished renaming files\n\nStart manual transcriptions')
    if not DEACTIVATE_TRANSCRIBE:
        transcribe_files()
    else:
        verbose_print('skipping transcribe because transcribing is not active')

    verbose_print('Fininished manual transcriptions\n\nStart sorting files')
    sort_files()

    verbose_print('Finished sorting files')
    verbose_print(f'\nFinished running script: {datetime.datetime.now()}\nTime elapsed: {datetime.datetime.now() - start_time}')
