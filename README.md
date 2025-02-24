# WhisperingAlchemy: Voice Recording Sorter

## Table of Contents

+ [About](#about)
+ [Getting Started](#getting_started)
  + [Prerequisites](#prerequisites)
+ [Installing the requirements](#installing)
  + [Using the Makefile](#installing_makefile)
+ [Running the code](#run_locally)
  + [Execution Options](#execution_options)
    + [main.py](#src_main)
    + [Usage Examples](#usage_examples)
+ [Todo](#todo)
+ [License](#license)

## About {#about}

Whispering Alchemy is a suite of scripts with one purpose:
Start with speech and voicenote files and end with sorted transcriptions in a semi-automated way.

The script defines a docker container to make it more portable and in my opinion, easier to set up.

Future releases should have a make file to make the setup even easier.

## Getting Started {#getting_started}

### Prerequisites {#prerequisites}

You need to have docker (or docker desktop) installed on your machine.
>I currently don't support running the script natively, those of you familiar with python should be able to get it working.

## Installing the requirements {#install}

### Using the Makefile {#install-make}

1. Install docker desktop
2. Run the command in the run_build_cmd.txt file
>Note you can skip this step if you already made an image, if you don't know what that means run step 2.
3. Make your own config file; start off by copying the example-config.toml to the scripts directory.
4. Run the command in the run_cmd.txt file