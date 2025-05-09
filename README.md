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

## About

Whispering Alchemy is a suite of scripts with one purpose:
Start with speech and voicenote files and end with sorted transcriptions.

The suite is based on a python script that can be containerized.

Most of the managment and processing scripts are written in clojure.

## Getting Started

### Prerequisites

- You need to have docker (or docker desktop) installed on your machine.
>I currently don't support running the script natively, those of you familiar with python should be able to get it working.

- Babahska TODO add link

## Installing the requirements

### Using the Makefile

1. Install docker desktop [or podman if that is your preference]
2. Clone this repository
3. Build the whisper-cpu container using one of the build commands under container-files
>Note you can skip this step if you already made an image, if you don't know what that means run step 2.