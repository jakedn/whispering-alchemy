This suite of scripts has one purpose:
Convert my speech and voicenotes to text and rename them. This should be done in an easy, automated fashion.

To make this portable I define a docker file and python scripts

In the future I plan to add a toml configuration file, so I can run it locally, in docker, or anywhere else.
The idea is to tweak the convert script and not hard code the directories; this will mean less changes to the repository.


# Usage
1. Install docker desktop
2. Run the command in the run_build_cmd.txt file
>Note you can skip this step if you already made an image, if you don't know what that means run step 2.
3. Run the command in the run_cmd.txt file