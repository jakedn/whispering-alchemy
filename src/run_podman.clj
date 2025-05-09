(ns run-podman
  (:require [babashka.process :as p]
            [babashka.fs :as fs]
            [clojure.string :as str]
            [babashka.pods :as pods]))

(def ^:dynamic *model-dir* (fs/expand-home "~/cvols-local/whisper-model-vol"))

(defn download-models
  "build the podman command that initially downloads all whisper models"
  [& opts]
  (apply concat ["podman" "run" "--rm" "-i"
                 "--name=whisper-app"
                 "-v" (str *model-dir* ":/model-dir:z")
                 ;"-v" (str tmp-dir ":/app:z")
                 "--tmpfs" "/app/tmp:size=1G"
                 "whisper-cpu" "--download-models"]
         opts))

(defn- command
  "build the podman command to be used with process/shell"
  [& opts]
  (apply concat ["podman" "run" "--rm" "-i"
                 "--name=whisper-app"
                 "--network" "none"
                 "-v" (str *model-dir* ":/model-dir:z")
                 ;"-v" (str tmp-dir ":/app:z")
                 "--tmpfs" "/app/tmp:size=1G"
                 "whisper-cpu"]
         opts))

(defn transcribe-audio
  "takes in a file path of an audio file and runs it through whispering alchemy container
   This function will return the stdout of the container and print the stderr to console
   Take note of the options from whispering alchemy."
  [file-path & opts]
  (let [file-ext (fs/extension file-path)
        new-opts (concat opts ["--audio-file-ext" file-ext])
        process-opts {:in (fs/file file-path) :out :string :err :string}
        command-vec (command new-opts)
        process (apply p/shell process-opts command-vec)]
    (println (:err process))
    (:out process)))

(defn get-words
  "Get the first few words of an audio file.
   Returns them as a vector."
  [file & opts]
  (->> (apply transcribe-audio file "--output" "words" opts)
       (#(str/split % #"\s+"))
       (remove str/blank?)
       vec))
